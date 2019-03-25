from ursapqUtils import UrsaPQ
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

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
        
        axslid = self.figure.add_axes([0.5, 0.93, 0.4, 0.04])
        self.filterSlider = Slider(axslid, 'Filter Lvl', 0, 0.9999, valinit=ursapq.data_filterLvl)
        self.filterSlider.on_changed(self.filterUpdate)
        
        self.stopEvent = Event() #Used to stop background thread when window closes
        self.figure.canvas.mpl_connect('close_event', self.stopUpdate)
        self.figure.show()
        
    def filterUpdate(self,val):
        ursapq.data_filterLvl = val

    def startUpdate(self):
        self.stopEvent.clear()
        self.thread = Thread(target=self.update, kwargs={'loop_forever':True} ).start()
        
    def stopUpdate(self, event):
        self.stopEvent.set()

    def update(self, loop_forever=False):
        while not self.stopEvent.is_set():
            self.figure.text(0.04, 0.93, "laser hit @ %s" % str(ursapq.data_laserTime) , fontsize=17)
        
            self.tofTrace.set_data(ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
            self.laserTrace.set_data(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
            if not loop_forever:
                break
                
    def draw(self):
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
            self.xdataId = 0
        else:
            self.xdataId = 1
    
        gs = gridspec.GridSpec(2, 2) #
    
        self.figure = plt.figure()
        self.figure.subplots_adjust(right=0.9, top=0.85, hspace=0.6)
        evenSlicepl = self.figure.add_subplot(gs[0,0])
        if not tof: evenSlicepl.set_xlim([0,xmax])
        evenSlicepl.set_title("SINGLE SHOT EVEN")
       
        oddSlicepl = self.figure.add_subplot( gs[0,1])
        if not tof: oddSlicepl.set_xlim([0,xmax])
        oddSlicepl.set_title("SINGLE SHOT ODD")       
        
        diffSlicepl = self.figure.add_subplot(gs[1,:])
        if not tof: diffSlicepl.set_xlim([0,xmax])
        diffSlicepl.set_title("SINGLE SHOT DIFFERENCE")               
        
        self.evenSlice, = evenSlicepl.plot( ursapq.data_evenShots[self.xdataId], ursapq.data_evenShots[2] )
        self.oddSlice,  = oddSlicepl.plot(  ursapq.data_oddShots[self.xdataId],  ursapq.data_oddShots[2] )
        self.diffSlice, = diffSlicepl.plot( ursapq.data_oddShots[self.xdataId],  
                                            ursapq.data_evenShots[2] - ursapq.data_oddShots[2])
                                            
        self.stopEvent = Event() #Used to stop background thread when window closes                                           
        self.figure.canvas.mpl_connect('close_event', self.stopUpdate)
        self.figure.show()

    def startUpdate(self):
        self.stopEvent.clear()
        self.thread = Thread(target=self.update, kwargs={'loop_forever':True} ).start()
        
    def stopUpdate(self, event):
        self.stopEvent.set()

    def update(self, loop_forever=False):
        while not self.stopEvent.is_set():
            self.evenSlice.set_data( ursapq.data_evenShots[self.xdataId], ursapq.data_evenShots[2] )
            self.oddSlice.set_data(  ursapq.data_oddShots[self.xdataId],  ursapq.data_oddShots[2] )
            self.diffSlice.set_data( ursapq.data_oddShots[self.xdataId],  
                                     ursapq.data_evenShots[2] - ursapq.data_oddShots[2])
            if not loop_forever:
                break

    def draw(self):
            self.figure.canvas.draw()
            self.figure.canvas.flush_events()


if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt

    ursapq = UrsaPQ()
    traces = TracePlots(ursapq)
    singleshots = SingleShot(ursapq, tof = False) #Set tof to true to plot TOF instead of eV
    
    Thread(target=traces.update,      kwargs={'loop_forever':True} ).start()
    Thread(target=singleshots.update, kwargs={'loop_forever':True} ).start()
    
    while True:
        try:
            traces.draw()
        except Exception:
            pass
        try:
            singleshots.draw()
        except Exception:
            pass
