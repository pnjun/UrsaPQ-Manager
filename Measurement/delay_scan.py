#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Delay')
run  = Run(daq=False, **scan.info)

scan.setup(integration_time =10,
           retarder = -20,
           coil = 0.2,
           waveplate = 0)
scan.sequence( deltest = np.arange(-500, -300, 50) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Run {run.daq.run_number}: Time Zero")

    even = data.even / data.gmd_even
    odd = data.odd / data.gmd_odd
    diff = even - odd

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
scan.on_update(plot.update_fig)

with run, plot:
    scan.run()

run.set_figure(plot.fig)
