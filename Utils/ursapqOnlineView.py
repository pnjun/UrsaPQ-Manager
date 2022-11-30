from ursapq_api import UrsaPQ
import matplotlib as mpl
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import numpy as np
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
        self.figure.subplots_adjust(right=0.9, top=0.80, hspace=0.6)
        gs = gridspec.GridSpec(2, 1) #
        
        self.eTofTracepl = self.figure.add_subplot(gs[0,0])
        self.eTofTracepl.set_title("eTOF TRACE")
        
        self.iTofTracepl = self.figure.add_subplot(gs[1,0])
        self.iTofTracepl.set_title("iTOF TRACE")
        #iTofTracepl.set_xlim([ ursapq.data_eTofTrace[0][0], ursapq.data_eTofTrace[0][-1]]) #set iTof timeaxis the same as eTof

        self.eTofTrace, = self.eTofTracepl.plot(ursapq.data_eTofTrace[0], ursapq.data_eTofTrace[1])
        self.iTofTrace, = self.iTofTracepl.plot(ursapq.data_iTofTrace[0], ursapq.data_iTofTrace[1])
        self.updateFreq = self.figure.text(0.04, 0.93, "", fontsize=13)
        
        
        axslid = self.figure.add_axes([0.5, 0.93, 0.4, 0.04])
        self.filterSlider = Slider(axslid, 'Filter Tau[s]', 0.1, 20, valinit=ursapq.data_filterTau)
        self.filterSlider.on_changed(self.filterUpdate)
        
        cfdax = self.figure.add_axes([0.5, 0.88, 0.4, 0.04])
        self.cfdFilterSlider = Slider(cfdax, 'CFD Threshold', 0, 10, valinit= ursapq.data_cfdThreshold if ursapq.data_cfdThreshold else 0)
        self.cfdFilterUpdate(self.cfdFilterSlider.val)
        self.cfdFilterSlider.on_changed(self.cfdFilterUpdate)
        
        axbutton = self.figure.add_axes([0.04, 0.84, 0.15, 0.06])
        self.autoscale_button = Button(axbutton, 'Autoscale y')
        self.autoscale_button.on_clicked(self.autoscaleCallback)        
        
        self.figure.show()
        
    def filterUpdate(self,val):
        ursapq.data_filterTau = val
        
    def cfdFilterUpdate(self, val):
        if val < 1:
            self.cfdFilterSlider.valtext.set_text("OFF")
            ursapq.data_cfdThreshold = None
        else:
            ursapq.data_cfdThreshold = val
    
    def autoscaleCallback(self, event):
        self.eTofTracepl.set_ylim( *calculate_autoscale( self.eTofTrace.get_ydata() ))
        self.iTofTracepl.set_ylim( *calculate_autoscale( self.iTofTrace.get_ydata() ))

    def update(self):
        self.updateFreq.set_text( f"Update Freq {ursapq.data_updateFreq:.1f}Hz" )
    
        self.eTofTrace.set_data(ursapq.data_eTofTrace[0], ursapq.data_eTofTrace[1])
        self.iTofTrace.set_data(ursapq.data_iTofTrace[0], ursapq.data_iTofTrace[1])

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
    def __init__(self, ursapq, tof = False, xmax=300):
        if tof:
            self.axId = 0
        else:
            self.axId = 1
    
        gs = gridspec.GridSpec(2, 1) #
    
        self.figure = plt.figure()
        self.figure.subplots_adjust(right=0.9, top=0.85, hspace=0.6)

        self.eTofSlicepl = self.figure.add_subplot(gs[0,0])
        if not tof: self.eTofSlicepl.set_xlim([0,xmax])
        self.eTofSlicepl.set_title("eTOF Sliced")
       
        self.iTofSlicepl = self.figure.add_subplot( gs[1,0])
        if not tof: self.iTofSlicepl.set_xlim([0,xmax])
        self.iTofSlicepl.set_title("iTOF Sliced")                   
        
        self.eTofSlice, = self.eTofSlicepl.plot( ursapq.data_axis[self.axId], ursapq.data_eTof_lowPass )
        self.iTofSlice, = self.iTofSlicepl.plot( ursapq.data_axis[self.axId], ursapq.data_iTof_lowPass )
                               
        axbutton = self.figure.add_axes([0.1, 0.9, 0.15, 0.06])
        self.autoscale_button = Button(axbutton, 'Autoscale y')
        self.autoscale_button.on_clicked(self.autoscaleCallback)        
                                            
        self.figure.show()

    def autoscaleCallback(self, event):
        self.eTofSlicepl.set_ylim( *calculate_autoscale( self.eTofSlice.get_ydata() ))
        self.iTofSlicepl.set_ylim( *calculate_autoscale( self.iTofSlice.get_ydata() ))

    def update(self):
        self.eTofSlice.set_data( ursapq.data_axis[self.axId], ursapq.data_eTof_lowPass )
        self.iTofSlice.set_data( ursapq.data_axis[self.axId], ursapq.data_iTof_lowPass )

        self.figure.canvas.draw()
        self.figure.canvas.flush_events()


if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt
    import numpy as np

    tof = True if "--tof" in sys.argv else False

    ursapq = UrsaPQ()
    traces = TracePlots(ursapq)
    singleshots = SingleShot(ursapq, tof = tof,xmax=220) #Set tof to true to plot TOF instead of eV
    
    while True:
        traces.update()
        singleshots.update()
 
