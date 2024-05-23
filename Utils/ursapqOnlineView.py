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
        self.figure = plt.figure()
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
        self.filterSlider = Slider(axslid, 'Filter Tau[s]', 0.5, 60, valinit=ursapq.data_filterTau)
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
    
        self.figure = plt.figure()
        self.figure.subplots_adjust(right=0.96, left=0.085, top=0.92, bottom=0.135,hspace=0.35)

        self.slice_ax = self.figure.add_subplot(gs[0])
        if not tof: self.slice_ax.set_xlim([0,xmax])
        self.slice_ax.set_title("SINGLE SHOT")

        self.diff_ax = self.figure.add_subplot(gs[1,:], sharex=self.slice_ax)
        self.diff_ax.set_title("SINGLE SHOT DIFFERENCE")               
        
        self.evenSlice, = self.slice_ax.plot( ursapq.data_axis[self.axId], ursapq.data_evenShots, label = 'even')
        self.oddSlice,  = self.slice_ax.plot( ursapq.data_axis[self.axId], ursapq.data_oddShots, label = 'odd' )
        self.diffSlice, = self.diff_ax.plot(  ursapq.data_axis[self.axId],  
                                              ursapq.data_evenShots - ursapq.data_oddShots)
        self.slice_ax.legend()

        #AUTOSCALE                                    
        self.axbutton = self.figure.add_axes([0.8, 0.018, 0.16, 0.055])
        self.autoscale_button = Button(self.axbutton, 'Autoscale y')
        self.autoscale_button.on_clicked(self.autoscaleCallback)        

        #MARKERS
        self.figure.text(0.08, 0.03, "Left/Right click on plot to place line markers. Middle click to clear", fontsize=8)

        self.figure.canvas.mpl_connect('button_press_event', self.set_marker)
        self.lines = []

        self.figure.show()

    def set_marker(self, event):
        if event.button == 2:
            while self.lines:
                self.lines.pop().remove()
            return

        if not event.inaxes or self.figure.canvas.toolbar.mode:
            return

        if event.inaxes == self.axbutton:
            return
        
        if event.button == 1: #Left click, h line only on clicked axis
            line = event.inaxes.axhline(event.ydata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            self.lines.append(line)
        if event.button == 3:  #Right click, v line on both axes
            line_a = self.diff_ax.axvline (event.xdata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            line_b = self.slice_ax.axvline(event.xdata, color='black', linestyle='--', alpha=0.7, linewidth=0.9)
            self.lines.append(line_a)
            self.lines.append(line_b)

    def autoscaleCallback(self, event):
        self.slice_ax.set_ylim( *calculate_autoscale( self.evenSlice.get_ydata() ))
        self.diff_ax.set_ylim( *calculate_autoscale( self.diffSlice.get_ydata() ))

    def update(self):
        self.evenSlice.set_data( ursapq.data_axis[self.axId], ursapq.data_evenShots )
        self.oddSlice.set_data(  ursapq.data_axis[self.axId], ursapq.data_oddShots  )
        self.diffSlice.set_data( ursapq.data_axis[self.axId],  
                                 ursapq.data_evenShots - ursapq.data_oddShots)

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
