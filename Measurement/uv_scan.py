#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure

from matplotlib import pyplot as plt
import numpy as np
import context 

scan = Scan.from_context(context, type='Uv Power')

ROI = slice(110,250)

scan.setup(integ_gmd = 200e3, #uJ
           #integ_time = 30, # s
           retarder = -100, # volts
           delay = 400, 
           coil = 800, #mA
           wiggle_ampl = 200) #mA
           
scan.sequence( waveplate = np.linspace(0, 45, 10)) 

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"UV Scan")

    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=ROI)
    diff = diff - diff.mean('evs')

    diff = np.abs(diff.sel(evs=ROI)).sum(dim='evs')
    if diff.squeeze().ndim > 0:
        diff.plot()
        
scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)
