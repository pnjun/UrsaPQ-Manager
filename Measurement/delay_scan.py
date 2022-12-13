from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
#Time zero estimate
TIME_ZERO  = 1456.85
PARK_DELAY = 1470
POLARIZ    = 'p'

INTEG_TIME = 60   #seconds, per bin
WAVEPLATE  = 16
RETARDER   = 10
PHOTON_EN  = 223

RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTMAX = 180 #Upper val of ev scale 

#Delays array

#delays = np.arange(-0.3, 1.01, .05)
#delays = np.array([0.7, 1, 2, 5, 10, 20, 50, 100, 200, 500])
delaysList = [[-0.3], np.arange(-.2, .41, .05), [.5,.6,.7]]
delays = np.concatenate(delaysList)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Delay{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*delays.shape[0]/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
set_waveplate(WAVEPLATE)
set_polarization(POLARIZ)
set_energy(PHOTON_EN)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs    = exp.data_axis[1]
data = np.empty((delays.shape[0], evs.shape[0]))
data[:] = np.NaN
even[:] = np.NaN
odd[:] = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, delays, data, sliceX = ev_slice)

#Generate random permutation
scan_order = np.arange(delays.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.delay) as run_id:
        plot.set_title(f"Run {run_id} - Delay Scan")
        
        for n in scan_order:
            print(f"Scanning delay: {delays[n]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_delay(delays[n], TIME_ZERO, PARK_DELAY)
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                even[n] = exp.data_evenAccumulator
                odd[n] = exp.data_oddAccumulator
                data[n] = even[n] - odd[n]
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
out_fname = OUTFOLDER + f"delay_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", delays=delays, evs=evs, diff=data, even=even, odd=odd)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")


