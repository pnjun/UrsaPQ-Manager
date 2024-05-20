#!/usr/bin/env python3
from matplotlib import pyplot as plt
import numpy as np

from fablive import Scan, Run, LiveFigure
import context 

scan = Scan.from_context(context, type='Time Zero')
run = Run(daq=False, proposal_id=False,**scan.info)

scan.setup(integration_time = 25)
scan.sequence( lam_dl = np.arange(4100, 4502, 100), repeat=True )

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

with run, plot:
    scan.run()


# ASK USER FOR TIME ZERO ESTIMATION

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

