from ursapq_api import UrsaPQ
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import sys

from threading import Thread
from threading import Event


#TOF AND LASER TRACES
class TracePlots:
    '''
    Plots TOF and Laser Trace for a whole macropulse
    '''
    def __init__(self, ursapq):
        self.figure = plt.figure()
        self.figure.subplots_adjust(right=0.9, top=0.85, hspace=0.6)
        gs = gridspec.GridSpec(3, 1) #
        
        tofTracepl   = self.figure.add_subplot(gs[:2,0])
        tofTracepl.set_title("ADC TOF TRACE")
        laserTracepl = self.figure.add_subplot(gs[2,0])
        laserTracepl.set_title("LASER TRACE")
        laserTracepl.set_xlim([ ursapq.data_tofTrace[0][0], ursapq.data_tofTrace[0][-1]]) #set laserTrace timeaxis the same as tofTrace

        self.tofTrace,   = tofTracepl.plot  (ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace, = laserTracepl.plot(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.updateFreq  = self.figure.text(0.04, 0.93, "", fontsize=15)
        
        
        axslid = self.figure.add_axes([0.5, 0.93, 0.4, 0.04])
        self.filterSlider = Slider(axslid, 'Filter Tau[s]', 0.5, 60, valinit=ursapq.data_filterTau)
        self.filterSlider.on_changed(self.filterUpdate)
        
        self.figure.show()
        
    def filterUpdate(self,val):
        ursapq.data_filterTau = val

    def update(self):
        self.updateFreq.set_text( f"Update Freq {ursapq.data_updateFreq:.1f}Hz" )
    
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
    def __init__(self, ursapq, tof = False, xmax=300):
        if tof:
            self.axId = 0
        else:
            self.axId = 1
    
        gs = gridspec.GridSpec(2, 2) #
    
        self.figure = plt.figure()
        self.figure.subplots_adjust(right=0.9, top=0.85, hspace=0.6)

        self.evenSlicepl = self.figure.add_subplot(gs[0,0])
        if not tof: self.evenSlicepl.set_xlim([0,xmax])
        self.evenSlicepl.set_title("SINGLE SHOT EVEN")
       
        self.oddSlicepl = self.figure.add_subplot( gs[0,1])
        if not tof: self.oddSlicepl.set_xlim([0,xmax])
        self.oddSlicepl.set_title("SINGLE SHOT ODD")       
        
        diffSlicepl = self.figure.add_subplot(gs[1,:])
        if not tof: diffSlicepl.set_xlim([0,xmax])
        diffSlicepl.set_title("SINGLE SHOT DIFFERENCE")               
        
        self.evenSlice, = self.evenSlicepl.plot( ursapq.data_axis[self.axId], ursapq.data_evenShots )
        self.oddSlice,  = self.oddSlicepl.plot(  ursapq.data_axis[self.axId], ursapq.data_oddShots )
        self.diffSlice, = diffSlicepl.plot( ursapq.data_axis[self.axId],  
                                            ursapq.data_evenShots - ursapq.data_oddShots)
                                            
        self.figure.show()

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
    traces = TracePlots(ursapq)
    singleshots = SingleShot(ursapq, tof = tof,xmax=300) #Set tof to true to plot TOF instead of eV
    
    while True:
        traces.update()
        singleshots.update()
 
