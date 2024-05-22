#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Delay High Power')

scan.setup(integ_gmd = 900e3, #seconds
           retarder = -0, # volts
           coil = 800, #mA
           waveplate = 45, #degree
           wiggle_ampl = 200) #mA
scan.sequence( delay = np.arange(-200, 1000, 200) ) #relative delay in fs

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Delay Scan")
    
    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=slice(0,80))
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
