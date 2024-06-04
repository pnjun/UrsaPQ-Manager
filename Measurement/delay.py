#!/usr/bin/env python3
from fablive import Scan, Run, LiveFigure

from matplotlib import pyplot as plt
import numpy as np
import context 
scan = Scan.from_context(context, type='Delay')

scan.setup(integ_gmd = 500e3, #uJ
           #integ_time = 60, # s
           retarder = -10, # volts
           coil = 800, #mA
           waveplate = 45, #degree
           wiggle_ampl = 200) #mA
           
#delay_arr = np.linspace(-1200,500,35 )  #fs
delay_arr = np.concatenate((np.linspace(-1000,-950,2),
                            np.linspace(-900,-600,13),
                            np.linspace(-550,-400,4), 
                            np.linspace(-300,0,4)
                            )) 
           
## coarse+fine delays
#scan.sequence( delay =  np.linspace(-250,2750,60) )
scan.sequence( delay = delay_arr)

plot = LiveFigure()
@plot.update
def updateplot(fig, data):
    fig.clear()
    fig.suptitle(f"Delay Scan")

    data = context.calibrate_evs(data)
    diff = data.even - data.odd
    diff = diff.sel(evs=slice(35,75))
#    diff = diff.sel(evs=slice(180,240))
    diff = diff - diff.mean('evs')

    if diff.squeeze().ndim == 1:
        diff.plot()
    if diff.squeeze().ndim == 2:
        diff.plot(cmap='RdBu')
        plt.gca().set_ylabel("delay [fs]")
        #plt.gca().set_yscale('symlog', linthresh=1000, linscale=1.4)
scan.on_update(plot.update_fig)

run = Run(**scan.info)
with run, plot:
    scan.run()

run.set_figure(plot.fig)
