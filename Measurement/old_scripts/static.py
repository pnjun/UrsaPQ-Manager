from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
INTEG_TIME = 600    #seconds, per bin
WAVEPLATE  = 45
RETARDER   = 5
POLARIZ    = 'p'
PHOTON_EN  = 30
DELAY      = -414
OUTFOLDER  = "./data/"

PLOTMAX = 50 #Upper val of ev scale 


#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD} Static {TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME/60:.1f} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
#set_waveplate(WAVEPLATE)
#set_polarization(POLARIZ)
#set_energy(PHOTON_EN)
#set_delay(delays[n])

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs    = exp.data_axis[1]
data = np.empty((1, evs.shape[0]))
data[:] = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, [1], data, sliceX = ev_slice)

try:
    with Run(RunType.static, skipDAQ=False) as run_id:
        plot.set_title(f"Run {run_id} - Static")
        
        #Reset accumulator for online preview
        exp.data_clearAccumulator = True
        
        #Set up preview updater 
        def updatef():
            diff_data = exp.data_evenAccumulator + exp.data_oddAccumulator
            data[0] = diff_data
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
np.savez(out_fname + ".npz", evs=evs, data=data)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














