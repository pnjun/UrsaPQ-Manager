from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
#Time zero estimate
TIME_ZERO  = 1457.05
DELAY      = .1

INTEG_TIME = 90    #seconds, per bin
WAVEPLATE  = 45
RETARDER   = 10 
POLARIZ    = 'p'

RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTMAX = 200 #Upper val of ev scale 

#energies array
energies = np.arange(214., 226.1, .5)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Photon Energy{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*energies.shape[0]/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
set_waveplate(WAVEPLATE)
set_delay(DELAY, TIME_ZERO)
set_polarization(POLARIZ)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs = exp.data_axis[1]

data        = np.empty((energies.shape[0], evs.shape[0]))
data[:]     = np.NaN
dataEven    = np.empty((energies.shape[0], evs.shape[0]))
dataEven[:] = np.NaN
dataOdd     = np.empty((energies.shape[0], evs.shape[0]))
dataOdd[:]  = np.NaN


#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, energies, data, sliceX = ev_slice)

#Generate random permutation
scan_order = np.arange(energies.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.energy) as run_id:
        plot.set_title(f"Run {run_id} - Energy Scan")
        
        for n in scan_order:
            print(f"Scanning energy: {energies[n]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_energy(energies[n])
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                dataEven[n] = exp.data_evenAccumulator
                dataOdd[n]  = exp.data_oddAccumulator
                data[n]     = dataEven[n] - dataOdd[n]
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
out_fname = OUTFOLDER + f"energy_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", energies=energies, evs=evs, dataEven=dataEven, dataOdd=dataOdd)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














