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

INTEG_TIME = 60   #seconds, per bin
PHOTON_EN  = 223

RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTMAX = 180 #Upper val of ev scale 

#Delays array

delaysList = [[-0.3], np.arange(-.2, .41, .05), [.5,.6,.7]]
delays = np.concatenate(delaysList)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Time Zero{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*delays.shape[0]/60:.1f} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()
set_energy(PHOTON_EN)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs = exp.data_axis[1] # use index 0 for tof, index 1 for evs

eTofData        = np.empty((energies.shape[0], evs.shape[0]))
eTofData[:]     = np.NaN
iTofData        = np.empty((energies.shape[0], evs.shape[0]))
iTofData[:]     = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
eTof_plot = DataPreview(evs, delays, eTofData, sliceX = ev_slice)
iTof_plot = DataPreview(evs, delays, iTofData, sliceX = ev_slice)

scan_order = np.arange(delays.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.delay) as run_id:
        eTof_plot.set_title(f"Delay {run_id} - eTOF")
        iTof_plot.set_title(f"Delay {run_id} - iTOF")
        
        for n in scan_order:
            print(f"Scanning delay: {delays[n]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_delay(delays[n], TIME_ZER0, PARK_DELAY)
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                eTofData[n] = exp.data_eTof_acc
                iTofData[n] = exp.data_iTof_acc
                eTof_plot.update_data(eTofData)
                eTof_plot.update_data(iTofData)
                
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
np.savez(out_fname + ".npz", energies=energies, evs=evs, eTofData=eTofData, iTofData=iTofData)
eTof_plot.save_figure(out_fname + "_eTof.png")
iTof_plot.save_figure(out_fname + "_iTof.png")

print(f"Data saved as {out_fname}")











