#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Delay')

scan.setup(integ_gmd = 450e3,
           retarder = -0,
           coil = 600,
           waveplate = 15,
           wiggle_ampl = 200)
scan.sequence( delay = np.arange(-500, 500, 100) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Delay Scan")
    
    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=slice(0,320))
    diff = diff - diff.mean('evs')

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)
