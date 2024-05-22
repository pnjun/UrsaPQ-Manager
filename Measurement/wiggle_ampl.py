#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Wiggler')
run  = Run(**scan.info)

scan.setup(integ_time = 60,
           retarder = -0,
           coil = 825,
           wiggle_freq = 0.5)
scan.sequence( wiggle_ampl = np.arange(0, 200, 10) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Wiggler Amplitude scan")
    data = context.calibrate_evs(data)
    data = data.sel(evs=slice(0, 320))
    eTof = data.even + data.odd    
    eTof.plot()

scan.on_update(plot.update_fig)

with run, plot:
    scan.run()

run.set_figure(plot.fig)
