from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************


INTEG_TIME = 300    #seconds, per bin
RANDOMIZE  = False
OUTFOLDER  = "./data/"

PLOTMAX = 200 #Upper val of ev scale 

#energies array
energies = np.arange(66., 80., .5)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Photon Energy{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*energies.shape[0]/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs = exp.data_axis[0] # use index 0 for tof, index 1 for evs

eTofData        = np.empty((energies.shape[0], evs.shape[0]))
eTofData[:]     = np.NaN
iTofData        = np.empty((energies.shape[0], evs.shape[0]))
iTofData[:]     = np.NaN


#Setup preview window
#ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
eTof_plot = DataPreview(evs, energies, eTofData, sliceX = None)
iTof_plot = DataPreview(evs, energies, iTofData, sliceX = None)

#Generate random permutation
scan_order = np.arange(energies.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.energy) as run_id:
        eTof_plot.set_title(f"Energy Scan {run_id} - eTOF")
        iTof_plot.set_title(f"Energy Scan {run_id} - iTOF")
        
        for n in scan_order:
            print(f"Scanning energy: {energies[n]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_energy(energies[n])
            
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
out_fname = OUTFOLDER + f"energy_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", energies=energies, evs=evs, eTofData=eTofData, iTofData=iTofData)
eTof_plot.save_figure(out_fname + "_eTof.png")
iTof_plot.save_figure(out_fname + "_iTof.png")

print(f"Data saved as {out_fname}")

