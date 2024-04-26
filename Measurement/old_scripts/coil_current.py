from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ
from time import sleep

#**************** SETUP PARAMETERS ************
POLARIZ    = 'p'

INTEG_TIME = 300    #seconds, per bin
WAVEPLATE  = 16
RETARDER   = 80 

OUTFOLDER  = "./data/"

#***************** CODE BEGINS ****************
print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Coil{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
set_waveplate(WAVEPLATE)
set_polarization(POLARIZ)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs    = exp.data_axis[1]
data   = np.empty(evs.shape[0])


try:
    with Run(RunType.coil) as run_id:
       print(f"Run {run_id} - accumulating data")
       exp.data_clearAccumulator = True
       sleep(INTEG_TIME)
            
except KeyboardInterrupt:
    print()
    print("Scan Stopped")
    interrupted = True
else:
    print()
    print(f"End of scan!")
    interrupted = False
    
data = exp.data_evenAccumulator - exp.data_oddAccumulator

#Setup output folder
from pathlib import Path
Path(OUTFOLDER).mkdir(parents=True, exist_ok=True)
out_fname = OUTFOLDER + f"coil_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", evs=evs, data=data)

print(f"Data saved as {out_fname}")
