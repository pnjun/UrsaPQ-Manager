#!/usr/bin/python
from ursapq_api import UrsaPQ
import matplotlib as mpl
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import sys

from threading import Thread
from threading import Event

mpl.rcParams['agg.path.chunksize'] = 10000

def calculate_autoscale(data, margin=1.1):
    d_min, d_max = np.min(data), np.max(data)
    
    center = (d_min + d_max) / 2
    width  = np.abs((d_max - d_min))*margin/2
    return center - width, center + width

#TOF AND LASER TRACES
class TracePlots:
    '''
    Plots TOF and Laser Trace for a whole macropulse
    '''
    def __init__(self, ursapq):
        self.figure = plt.figure('UrsaPQ trace view')
        self.figure.subplots_adjust(right=0.9, top=0.80, bottom=0.08, hspace=0.6)
        gs = gridspec.GridSpec(3, 1) #
        
        self.tofTracepl   = self.figure.add_subplot(gs[:2,0])
        self.tofTracepl.set_title("ADC TOF TRACE")
        self.laserTracepl = self.figure.add_subplot(gs[2,0])
        self.laserTracepl.set_title("LAM TRACE")

        self.tofTrace,   = self.tofTracepl.plot  (ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace, = self.laserTracepl.plot(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.updateFreq  = self.figure.text(0.04, 0.95, "", fontsize=11)
        
        
        axslid = self.figure.add_axes([0.42, 0.87, 0.48, 0.04])
        self.filterSlider = Slider(axslid, 'Filter Tau[s] ', 0, 60, valinit=ursapq.data_filterTau)
        self.filterSlider.on_changed(self.filterUpdate)
        
        axbutton = self.figure.add_axes([0.04, 0.87, 0.15, 0.06])
        self.autoscale_button = Button(axbutton, 'Autoscale y')
        self.autoscale_button.on_clicked(self.autoscaleCallback)      
        
        self.figure.show()
        
    def filterUpdate(self,val):
        ursapq.data_filterTau = val

    def autoscaleCallback(self, event):
        self.tofTracepl.set_ylim( *calculate_autoscale( self.tofTrace.get_ydata() ))
        self.laserTracepl.set_ylim( *calculate_autoscale( self.laserTrace.get_ydata() ))

    def update(self):
        self.updateFreq.set_text( f"Updates @ {ursapq.data_updateFreq:.1f}Hz - GMD rate: {ursapq.gmd_rate:.0f} uJ/s" )
    
        self.tofTrace.set_data(ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace.set_data(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])

        self.filterSlider.set_val( ursapq.data_filterTau )
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

#SINGLE SHOT AVERAGES
class SingleShot:
    '''
    Plots single shot data. If tof is True, x-axis shows time of flight, 
    if tof is false, x-axis are eV.
    
    xmax is x-axis limit when plotting eV
    '''
    def __init__(self, ursapq,  xmax, tof = False):
        if tof:
            self.axId = 0
        else:
            self.axId = 1
    
        #PLOT SETUP
        gs = gridspec.GridSpec(2, 1) #
    
        self.figure = plt.figure('UrsaPQ slice view')
        self.figure.subplots_adjust(right=0.96, left=0.085, top=0.86, bottom=0.14,hspace=0.3)

        self.slice_ax = self.figure.add_subplot(gs[0])
        if not tof: self.slice_ax.set_xlim([0,xmax])

        self.diff_ax = self.figure.add_subplot(gs[1,:], sharex=self.slice_ax)         
        
        data = ursapq.data_shots_filtered

        self.evenSlice, = self.slice_ax.plot( ursapq.data_axis[self.axId], data[0], label = 'even')
        self.oddSlice,  = self.slice_ax.plot( ursapq.data_axis[self.axId], data[1], label = 'odd' )
        self.diffSlice, = self.diff_ax.plot(  ursapq.data_axis[self.axId], data[0] - data[1], label='even+odd')
        self.diff_ax.axhline(0, color='black', linestyle=':', alpha=0.9, linewidth=0.9)
        self.slice_ax.legend()
        self.diff_ax.legend(loc='upper right')

        #AUTOSCALE                                    
        self.init_autoscale()
        self.init_delay_indicator()
        self.init_markers_callbacks()

        self.figure.show()

    def init_autoscale(self):
        self.axbutton = self.figure.add_axes([0.8, 0.018, 0.16, 0.055])
        self.autoscale_button = Button(self.axbutton, 'Autoscale y')
        self.autoscale_button.on_clicked(self.autoscaleCallback)     

    def init_delay_indicator(self):
        self.figure.text(0.085, 0.93, "Current delay:", fontsize=11)
        self.delay_axis  = plt.axes([0.27,0.92,0.68,0.04], facecolor=(1,1,1,0))

        self.delay_axis.spines['bottom'].set_position('center')

        # Eliminate other axes
        self.delay_axis.spines['left'].set_color('none')
        self.delay_axis.spines['right'].set_color('none')
        self.delay_axis.spines['top'].set_color('none')
        self.delay_axis.get_yaxis().set_ticks([])

        self.delay_axis.set_xscale('symlog',  linthresh=1, linscale=1.4)
        ticks = [-10,-1,0,1,10,100]
        self.delay_axis.get_xaxis().set_ticks(ticks, labels=ticks)

        minor_ticks = np.arange(-1, 1, 0.1)
        minor_ticks = np.append(minor_ticks, np.arange(-10, 10, 1))
        minor_ticks = np.append(minor_ticks, np.arange(0, 100, 10))
        minor_ticks = np.append(minor_ticks, np.arange(0, 1000, 100))
        self.delay_axis.get_xaxis().set_ticks(minor_ticks, minor=True)
        
        self.delay_line = None

        self.delay_axis.set_xlim([-20,500])

    def init_markers_callbacks(self):
        self.figure.text(0.08, 0.03, "Left/Right click on plot to place line markers. Middle click to clear", fontsize=8)
        self.figure.canvas.mpl_connect('button_press_event', self.set_marker)
        self.lines = []

    def set_marker(self, event):
        if not event.inaxes or self.figure.canvas.toolbar.mode:
            return

        if event.button == 2:
            while self.lines:
                self.lines.pop().remove()
            return

        if event.inaxes not in [self.diff_ax, self.slice_ax]:
            return
        
        if event.button == 1: #Left click, h line only on clicked axis
            line = event.inaxes.axhline(event.ydata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            self.lines.append(line)
        if event.button == 3:  #Right click, v line on both axes
            line_a = self.diff_ax.axvline (event.xdata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            line_b = self.slice_ax.axvline(event.xdata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            self.lines.extend([line_a, line_b])

    def autoscaleCallback(self, event):
        self.slice_ax.set_ylim( *calculate_autoscale( self.evenSlice.get_ydata() ))
        self.diff_ax.set_ylim( *calculate_autoscale( self.diffSlice.get_ydata() ))

    def update(self):
        data = ursapq.data_shots_filtered

        curr_delay = ursapq.data_delay
        if self.delay_line:
            self.delay_line.remove()
            self.delay_text.remove()
        self.delay_text = self.delay_axis.text(curr_delay, 1.1, f"{curr_delay:.3f} ps", ha='center', fontfamily='monospace', fontsize='medium')
        self.delay_line = self.delay_axis.axvline(curr_delay, color='red', linewidth=2.2)

        self.evenSlice.set_data( ursapq.data_axis[self.axId], data[0] )
        self.oddSlice.set_data(  ursapq.data_axis[self.axId], data[1]  )
        self.diffSlice.set_data( ursapq.data_axis[self.axId], data[0] + data[1])

        self.figure.canvas.draw()
        self.figure.canvas.flush_events()


if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt
    import numpy as np

    tof = True if "--tof" in sys.argv else False

    ursapq = UrsaPQ()
    singleshots = SingleShot(ursapq, tof = tof, xmax=450) #Set tof to true to plot TOF instead of eV
    traces = TracePlots(ursapq)
    
    while True:
        traces.update()
        singleshots.update()

        if len(plt.get_fignums()) < 2:
            break
