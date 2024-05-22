#!/usr/bin/env python3
from matplotlib import pyplot as plt
import numpy as np

from fablive import Scan, Run, LiveFigure
import context 

# Parameters for binary search,
# scan will first scan at START and STOP, then
# it will scan at (START + STOP) / 2
# euclidean distance between the mid point and the START and STOP
# will be calculated to evaluate similarity between the spectras
# at the two points. If the mid is more similar to START, then the
# MID will be the new START, if it is more similar to STOP, then the
# MID will be the new STOP. The scan will then be repeated
# until START-STOP < TOLERANCE

START = 3949.5
STOP  = 3951.5
TOLERANCE = 0.050 # 50fs tolerance
ROI = slice(35,50)

scan = Scan.from_context(context, type='Time Zero')

scan.setup(integ_gmd = 80e3,
           retarder = -0,
           coil = 800,
           waveplate = 45,
           wiggle_ampl = 200)

def distance(data, t1, t2):
    ''' calculates the "distance" between the spectras 
        at time t1 and t2.
        
        Used to evaluate how 'similar' the two spectras are
    '''
    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=ROI)
    diff = diff - diff.mean('evs')

    #Differential intensity (how much differential signal is there?)
    t1_int = np.abs(diff.sel(lam_dl=t1)).sum()
    t2_int = np.abs(diff.sel(lam_dl=t2)).sum()

    return np.abs(t1_int - t2_int)

@scan.sequence
def binary_search():
    ''' Binary search for time zero  '''
    global START, STOP
    yield from [{'lam_dl': START}, {'lam_dl': STOP}] # First scan at START and STOP

    while abs(START - STOP) > TOLERANCE:
        mid = (START + STOP) / 2
        yield {'lam_dl': mid}
        start_diff = distance(scan.data, START, mid)
        stop_diff = distance(scan.data, STOP, mid)

        if start_diff < stop_diff:
            START = mid
        else:
            STOP = mid
    
    # Last mid point is time zero estimate
    context.set_t0(mid)     

plot = LiveFigure()
@plot.update
def update_figure(fig, data):
    ''' live plot definition '''
    fig.clear()
    fig.suptitle(f"Time Zero")
    
    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=ROI)
    diff = diff - diff.mean('evs')

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
scan.on_update(plot.update_fig)


# RUN THE SCAN
run = Run(**scan.info)
with run, plot:
    scan.run()


# ASK USER TO VERIFY ZERO ESTIMATION
fig = plt.figure()
update_figure(fig, scan.data)
t0 = context.get_t0()
t0_line = plt.axhline(t0, color='black', linestyle='--')
fig.suptitle(f"Current time zero estimate: {t0:.3f} \n click on the plot to update")

#grab y position of click for time zero estimation
def grab_t0(event):
    t0 = event.ydata
    fig.suptitle(f"Current time zero estimate: {t0:.3f} \n click on the plot to update")
    context.set_t0(t0)
    t0_line.set_ydata([t0])
    fig.canvas.draw_idle()

fig.canvas.mpl_connect('button_press_event', grab_t0)

plt.show()
run.set_figure(fig)


