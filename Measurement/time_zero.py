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

START = 4000
STOP  = 4500
TOLERANCE = 0.050 # 50fs tolerance


scan = Scan.from_context(context, type='Time Zero')
run = Run(daq=False, proposal_id=False,**scan.info)

scan.setup(integration_time = 30)

def distance(data, t1, t2):
    ''' calculates the "distance" between the spectras 
        at time t1 and t2.
        
        Used to evaluate how 'similar' the two spectras are
    '''
    diff_t1 = data.sel(lam_dl=t1).even - data.sel(lam_dl=t1).odd
    diff_t2 = data.sel(lam_dl=t2).even - data.sel(lam_dl=t2).odd

    return np.linalg.norm(diff_t1 - diff_t2) # Sum of square

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
    
    # Last mid point is the time zero
    context.set_t0(mid)     

plot = LiveFigure()
@plot.update
def update_figure(fig, data):
    fig.clear()
    fig.suptitle(f"Run {run.daq.run_number}: Time Zero")

    diff = (data.even - data.odd)
    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
scan.on_update(plot.update_fig)


# RUN THE SCAN
with run, plot:
    scan.run()

print(scan.info)

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


