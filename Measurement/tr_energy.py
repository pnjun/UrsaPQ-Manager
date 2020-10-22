from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
#Time zero estimate
TIME_ZERO  = 1456.5
PARK_DELAY = 1470

INTEG_TIME = 30    #seconds, per bin
WAVEPLATE  = 25
RETARDER   = 30 
POLARIZ    = 's'

RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTROI = (120,160) #Integration region for online plot 

#Delays array
energies = np.arange(155., 170.1, 1)
delays = np.arange(-0.1, 0.3, 0.1)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}Time Resolved Energy{TermCol.ENDC} Scan")
print(f"{TermCol.RED}{TermCol.BOLD}Is the DAQ running?{TermCol.ENDC}")
print(f"Time to scan {INTEG_TIME*energies.shape[0]*delays.shape[0]/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
set_waveplate(WAVEPLATE)
set_polarization(POLARIZ)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs = exp.data_axis[1]
ROI = slice(np.argmin(np.abs(evs - PLOTROI[1])), 
            np.argmin(np.abs(evs - PLOTROI[0])) )

data        = np.empty((delays.shape[0], energies.shape[0]))
data[:]     = np.NaN
dataEven    = np.empty((delays.shape[0], energies.shape[0], evs.shape[0]))
dataEven[:] = np.NaN
dataOdd     = np.empty((delays.shape[0], energies.shape[0], evs.shape[0]))
dataOdd[:]  = np.NaN


#Setup preview window
plot = DataPreview(energies, delays, data)

#Generate scan order sequence
X,Y = np.meshgrid(np.arange(energies.shape[0]),np.arange(delays.shape[0]))
scan_order = np.array([X.flatten(),Y.flatten()]).T

#Generate random permutation
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

print(ROI)
exit()
try:
    with Run(RunType.tr_energy) as run_id:
        plot.set_title(f"Run {run_id} - Time Resolved Energy Scan")
        
        for e, d in scan_order:
            print(f"Scanning energy {energies[e]:.1f} delay {delays[d]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_energy(energies[e])
            set_delay(delays[d], TIME_ZERO, PARK_DELAY)
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                dataEven[n] = exp.data_evenAccumulator
                dataOdd[n]  = exp.data_oddAccumulator
                data[n]     = (dataEven[n] - dataOdd[n])[:,:,ROI].sum(axis=2)
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
out_fname = OUTFOLDER + f"trEnergy_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", energies=energies, delays=delays, evs=evs,  
                             dataEven=dataEven, dataOdd=dataOdd)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














