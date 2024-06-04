#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np
import context 

scan = Scan.from_context(context, type='Coil')
run  = Run(**scan.info)

scan.setup(integ_gmd = 120e3, #uJ
           retarder = -18,
           wiggle_ampl = 0) # mA
scan.sequence( coil = np.arange(500, 1000, 20) )

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Coil Scan")
    data = context.calibrate_evs(data)
    data = data.sel(evs=slice(25, 50))
    eTof = data.even - data.odd    
    eTof.plot()

scan.on_update(plot.update_fig)

with run, plot:
    scan.run()

run.set_figure(plot.fig)
