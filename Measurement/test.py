#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np

import context 

scan = Scan(context = context)

scan.setup( retarder = 90,
            waveplate = 35,
            coil = 0.5)

scan.sequence( delay = np.arange(0, 100, 40),
               energy = ["M1", "M2", "M3"])

scan.gather(context.gather_data)

plot = LiveFigure()

@plot.update
def updateplot(fig, data):
    fig.suptitle("Difference between even and odd shots")
    fig.clear()

    diff = (data.even - data.odd).mean('eTof')
    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
        
scan.on_update(plot.update_fig)


daq  = Run(daq=False, proposal_id=False,**scan.info)
with daq, plot:
    scan.run()