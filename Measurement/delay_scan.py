#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np

import context 

scan = Scan.from_context(context, type='Delay')

scan.setup(integration_time = 70)

scan.sequence( deltest = np.arange(-700, -300, 50) )

plot = LiveFigure(savefig='test.png')

@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle("Difference between even and odd shots")

    diff = (data.even - data.odd)
    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
        
scan.on_update(plot.update_fig)

daq  = Run(daq=False, proposal_id=11013415,**scan.info)
with daq, plot:
    scan.run()

import pickle
with open('figure.pkl', 'wb') as f:
    pickle.dump(plot.fig, f)
