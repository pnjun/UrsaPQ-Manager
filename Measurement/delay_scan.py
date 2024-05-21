#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Delay')

scan.setup(integ_time =10,
           retarder = -0,
           coil = 0.2)
scan.sequence( delay = np.arange(-500, 500, 50) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Delay Scan")
    
    data = context.calibrate_evs(data)
    diff = data.even - data.odd

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
scan.on_update(plot.update_fig)

with Run(**scan.info), plot:
    scan.run()

run.set_figure(plot.fig)
