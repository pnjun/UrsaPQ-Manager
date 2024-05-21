#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import context 

ROI = slice(25,40)

scan = Scan.from_context(context, type='UV Raster')
scan.setup(integ_time = 30,
           retarder = -0)

scan.sequence( uv_steering_h = np.arange(0, 200, 15) )


plot = LiveFigure()
@plot.update
def update_figure(fig, data):
    fig.clear()
    fig.suptitle(f"UV Raster Scan")

    diff = data.even - data.odd
    diff = np.abs(diff.sel(evs=ROI)).sum(dim='evs')
    if diff.squeeze().ndim > 0:
        diff.plot()


scan.on_update(plot.update_fig)

with plot:
    scan.run()

fig = plt.figure()
update_figure(plot.fig, scan.data)