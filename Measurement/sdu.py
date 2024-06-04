#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure

from matplotlib import pyplot as plt
import numpy as np
import context 
scan = Scan.from_context(context, type='Delay')

scan.setup(integ_gmd = 50e3, #uJ
           integ_time = 120, # s
           retarder = -90, # volts
           coil = 800, #mA
           wiggle_ampl = 250) #mA

           
scan.sequence( sdu = np.linspace(-0.5, .5, 11) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Delay Scan")

    data = context.calibrate_evs(data)
    diff = data.even + data.odd
    diff = diff.sel(evs=slice(95,120))
    diff = diff - diff.mean('evs')

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
        plt.gca().set_ylabel("delay [fs]")
scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)
