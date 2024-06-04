#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

UV_ONLY = True
LABEL = 'UV Only' if UV_ONLY else 'Static'

scan = Scan.from_context(context, type=LABEL)

scan.setup(integ_gmd = 600e3, #uJ
           retarder = -15, # volts
           coil = 800, #mA
           wiggle_ampl = 200) #mA
scan.sequence( null = [0] ) #no sequence

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"{LABEL} Scan")

    data = context.calibrate_evs(data)
    diff = data.even - data.odd

    diff = diff.sel(evs=slice(0,80))
    diff = diff - diff.mean('evs')
    diff.plot()

scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)



