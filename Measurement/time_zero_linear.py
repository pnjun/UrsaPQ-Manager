#!/usr/bin/env python3
from matplotlib import pyplot as plt
import numpy as np

from fablive import Scan, Run, LiveFigure
import context 

ROI = slice(25,60)

scan = Scan.from_context(context, type='Time Zero')

scan.setup(integ_gmd = 100e3,
           retarder = -18,
           coil = 800,
           waveplate = 15,
           wiggle_ampl = 200)

scan.sequence( lam_dl =  np.linspace(3946.0, 3946.6, 25) )

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

run = Run(**scan.info)
with run, plot:
    scan.run()


# ASK USER FOR TIME ZERO ESTIMATION

fig = plt.figure()
update_figure(fig, scan.data)
t0 = context.get_t0()
t0_line = plt.axhline(t0, color='black', linestyle='--')
fig.suptitle(f"Previous time zero estimate: {t0:.3f} \n click on the plot to update")

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
