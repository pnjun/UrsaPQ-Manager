from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
INTEG_TIME = 60    #seconds, per bin
WAVEPLATE = 45
OUTFOLDER  = "./data/"
DIRECTION = "vertical" # vertical or horizontal
PLOTMAX = 26 #Upper val of ev scale 

STEPNUM = 10
STEPSIZE = 10

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}RASTER SCAN UV{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*STEPNUM/60:.1f} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

set_waveplate(WAVEPLATE)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs    = exp.data_axis[1]
data = np.empty((STEPNUM, evs.shape[0]))
data[:] = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, range(STEPNUM), data, sliceX = ev_slice)


if DIRECTION == "vertical":
    run_type = RunType.raster_v
    address = "FLASH.LASER/MOD24.PICOMOTOR/Steering_PMC/MOTOR.2.MOVE.REL"
elif DIRECTION == "horizontal":
    run_type = RunType.raster_h
    address = "FLASH.LASER/MOD24.PICOMOTOR/Steering_PMC/MOTOR.1.MOVE.REL"
else:
    raise ValueError("Direction must be either horizontal or vertical")

try:
    with Run(run_type, skipDAQ=False) as run_id:
        plot.set_title(f"Run {run_id} - Raster {DIRECTION}")
        
        for n in range(STEPNUM):
            print(f"Step num {n}", end= "\r")
            
            #MOVE UV POINTING
            if n != 0:
                pydoocs.write(address, STEPSIZE)
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                diff_data = exp.data_evenAccumulator - exp.data_oddAccumulator
                data[n] = diff_data
                plot.update_data(data)
                
            #Wait for INTEG_TIME while updating the preview
            DataPreview.update_wait(updatef, INTEG_TIME)
            
except KeyboardInterrupt:
    print()
    print("Scan Stopped")
    interrupted = True
else:
    print()
    print(f"End of scan!")
    interrupted = False
            
#Setup output folder
from pathlib import Path
Path(OUTFOLDER).mkdir(parents=True, exist_ok=True)
out_fname = OUTFOLDER + f"raster_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", steps=range(STEPNUM), evs=evs, data=data)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














