from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
TIME_ZERO = -448.9

INTEG_TIME = 30    #seconds, per bin
DELAY      = 0.2     #ps
WAVEPLATE  = 45
POLARIZ    = 'p'
DIFFERENCE = False
RANDOMIZE  = False

OUTFOLDER  = "./data/"
PLOTMAX = 30 #Upper val of ev scale 

#Delays array
#retarders = -np.concatenate([np.arange(0,10,2) , np.arange(10, 65, 5)])
retarders = -np.arange(5.5,15.5,0.5) 

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Retardation Scan{TermCol.ENDC} Scan")
print(f"Time to scan {INTEG_TIME*retarders.shape[0]/ 60} min")
print()

exp = UrsaPQ()
startDate = datetime.now()

set_waveplate(WAVEPLATE)
set_delay(DELAY, TIME_ZERO)
set_polarization(POLARIZ)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
tof    = exp.data_axis[0]
data = np.empty((retarders.shape[0], tof.shape[0]))
data[:] = np.NaN

#Setup preview window
plot = DataPreview(tof, retarders, data, diff=DIFFERENCE)

#Generate random permutation
scan_order = np.arange(retarders.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.retardation) as run_id:
        plot.set_title(f"Run {run_id} - Retardation Scan")
        
        for n in scan_order:
            print(f"Scanning retarder: {retarders[n]:.3f}", end= "\r")
            
            #Set the desired retardation stage position 
            exp.tof_retarderSetHV = retarders[n]
            time.sleep(2)
            
            #Wait for voltage 
            tries = 0
            while (np.abs(exp.tof_retarderSetHV - exp.tof_retarderHV) > 0.5) and (tries < 10):
                time.sleep(1)
                tries += 1
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                if DIFFERENCE:
                    databin = exp.data_evenAccumulator - exp.data_oddAccumulator
                else:
                    databin = exp.data_evenAccumulator + exp.data_oddAccumulator
                data[n] = databin
                    
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
out_fname = OUTFOLDER + f"retarder_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", retarders=retarders, tof=tof, data=data)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")






