from ursapqUtils import UrsaPQ


#TOF AND LASER TRACES
class TracePlots:
    def __init__(self, ursapq):
        self.figure = plt.figure()
        tofTracepl   = self.figure.add_subplot(211)
        laserTracepl = self.figure.add_subplot(212)

        self.tofTrace,   = tofTracepl.plot  (ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace, = laserTracepl.plot(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.figure.show()

    def update(self):
        self.tofTrace.set_data(ursapq.data_tofTrace[0], ursapq.data_tofTrace[1])
        self.laserTrace.set_data(ursapq.data_laserTrace[0], ursapq.data_laserTrace[1])
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

#SINGLE SHOT AVERAGES
class SingleShotPlots:
    def __init__(self, ursapq):
        self.figure = plt.figure()
        tofSlicepl = self.figure.add_subplot(111)

        self.tofSlice, = tofSlicepl.plot( ursapq.data_tofSingleShot )
        self.figure.show()

    def update(self):
        self.tofSlice.set_ydata(ursapq.data_tofSingleShot)
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()


if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt

    ursapq = UrsaPQ()
    traces = TracePlots(ursapq)
    singleshots = SingleShotPlots(ursapq)

    while True:
        traces.update()
        singleshots.update()
