#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

#CURERNT 0.201
ROI = slice(35,50)

scan = Scan.from_context(context, type='Rotation')

scan.setup(integ_gmd = 80e3,
           retarder = -0,
           coil = 800,
           waveplate = 45,
           wiggle_ampl = 200)
scan.sequence( rotation = np.arange(-0.503, -0.487, 0.001) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"UV Rotation Scan")
    
    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=slice(0,320))
    diff = diff - diff.mean('evs')

    diff = np.abs(diff.sel(evs=ROI)).sum(dim='evs')
    if diff.squeeze().ndim > 0:
        diff.plot()

scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)
