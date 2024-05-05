#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure
import numpy as np

import context 

scan = Scan.from_context(context)

scan.setup(integration_time = 20)

scan.sequence( deltest = np.arange(-500, -300, 50) )

#plot = LiveFigure()

# @plot.update
# def updateplot(fig, data):
#     fig.clear()
#     fig.suptitle("Difference between even and odd shots")


#     diff = (data.even - data.odd)
#     if diff.squeeze().ndim == 1:
#         diff.plot()
#     if diff.squeeze().ndim == 2:
#         diff.plot(cmap='RdBu')
        
# scan.on_update(plot.update_fig)

daq  = Run(daq=False, proposal_id=False,**scan.info)
with daq:
    scan.run()
