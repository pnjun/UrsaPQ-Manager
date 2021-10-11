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
        gs = gridspec.GridSpec(2, 1) #
        
        eTofTracepl = self.figure.add_subplot(gs[0,0])
        eTofTracepl.set_title("eTOF TRACE")
        
        iTofTracepl = self.figure.add_subplot(gs[1,0])
        iTofTracepl.set_title("iTOF TRACE")
        #iTofTracepl.set_xlim([ ursapq.data_eTofTrace[0][0], ursapq.data_eTofTrace[0][-1]]) #set iTof timeaxis the same as eTof

        self.eTofTrace, = eTofTracepl.plot(ursapq.data_eTofTrace[0], ursapq.data_eTofTrace[1])
        self.iTofTrace, = iTofTracepl.plot(ursapq.data_iTofTrace[0], ursapq.data_iTofTrace[1])
        self.updateFreq = self.figure.text(0.04, 0.93, "", fontsize=15)
        
        
        axslid = self.figure.add_axes([0.5, 0.93, 0.4, 0.04])
        self.filterSlider = Slider(axslid, 'Filter Tau[s]', 0.5, 60, valinit=ursapq.data_filterTau)
        self.filterSlider.on_changed(self.filterUpdate)
        
        self.figure.show()
        
    def filterUpdate(self,val):
        ursapq.data_filterTau = val

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
        
        self.eTofSlice, = self.eTofSlicepl.plot(  ursapq.data_axis[self.axId], ursapq.data_evenShots )
        self.iTofSlice,  = self.iTofSlicepl.plot( ursapq.data_axis[self.axId], ursapq.data_oddShots )
                                            
        self.figure.show()

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
    singleshots = SingleShot(ursapq, tof = tof,xmax=300) #Set tof to true to plot TOF instead of eV
    
    while True:
        traces.update()
        singleshots.update()
 
