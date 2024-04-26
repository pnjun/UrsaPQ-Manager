from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ
import time

#**************** SETUP PARAMETERS ************
INTEG_TIME = 30    #seconds, per bin
WAVEPLATE  = 45
RETARDER   = 11
POLARIZ    = 'p'
PHOTON_EN  = 30

RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTMAX = 27 #Upper val of ev scale 

#Delays array
#Rough time zero at 1456.388
delays = np.arange(-5, +5, 1.) - 448.9

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Time Zero{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*delays.shape[0]/60:.1f} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
time.sleep(5)
set_waveplate(WAVEPLATE)
#set_polarization(POLARIZ)
#set_energy(PHOTON_EN)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs    = exp.data_axis[1]
data = np.empty((delays.shape[0], evs.shape[0]))
data[:] = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, delays, data, sliceX = ev_slice)

scan_order = np.arange(delays.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.time_zero, skipDAQ=False) as run_id:
        plot.set_title(f"Run {run_id} - Time Zero")
        
        for n in scan_order:
            print(f"Scanning delay: {delays[n]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_delay(delays[n])
            
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
out_fname = OUTFOLDER + f"timeZero_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", delays=delays, evs=evs, data=data)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














