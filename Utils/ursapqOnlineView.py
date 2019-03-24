from ursapqUtils import UrsaPQ


#TOF AND LASER TRACES
class TracePlots:
    '''
    Plots TOF and Laser Trace for a whole macropulse
    '''
    def __init__(self, ursapq):
        self.figure = plt.figure()
        tofTracepl   = self.figure.add_subplot(211)
        tofTracepl.set_title("ADC TOF TRACE")
        laserTracepl = self.figure.add_subplot(212)
        laserTracepl.set_title("LASER TRACE")
                
        self.tofTrace,   = tofTracepl.plot  (ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace, = laserTracepl.plot(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.figure.show()

    def update(self):
        self.tofTrace.set_data(ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace.set_data(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

#SINGLE SHOT AVERAGES
class SingleShot_tof:
    '''
    Plots single shot TOF data
    '''
    def __init__(self, ursapq):
        self.figure = plt.figure()
        slicepl = self.figure.add_subplot(111)
        slicepl.set_title("SINGLE SHOT TOF SPECTRUM")
        
        if ursapq.data_SingleShot_tof is not None:
            self.slice, = slicepl.plot( ursapq.data_SingleShot_tof[0], ursapq.data_SingleShot_tof[1] )
            self.figure.show()
        else:
            print("No single shot data")

    def update(self):
        try:
            self.slice.set_data( ursapq.data_SingleShot_tof[0], ursapq.data_SingleShot_tof[1] )
            self.figure.canvas.draw()
            self.figure.canvas.flush_events()
        except Exception:
            pass

class SingleShot_eV:
    '''
    Plots single shot TOF data as a function of electronVolts
    '''
    def __init__(self, ursapq, xmax=300):
        self.figure = plt.figure()
        slicepl = self.figure.add_subplot(111)
        slicepl.set_xlim([0,xmax])
        slicepl.set_title("SINGLE SHOT ENERGY SPECTRUM")
        
        if ursapq.data_SingleShot_eV is not None:
            self.slice, = slicepl.plot( ursapq.data_SingleShot_eV[0], ursapq.data_SingleShot_eV[1] )
            self.figure.show()
        else:
            print("No single shot data")

    def update(self):
        try:
            self.slice.set_data( ursapq.data_SingleShot_eV[0], ursapq.data_SingleShot_eV[1] )
            self.figure.canvas.draw()
            self.figure.canvas.flush_events()
        except Exception:
            pass




if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt

    ursapq = UrsaPQ()
    traces = TracePlots(ursapq)
    singleshots = SingleShot_eV(ursapq)
    while True:
        traces.update()
        singleshots.update()
