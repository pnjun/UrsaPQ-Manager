import scan_utils as su
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************

#Time zero estimate
TIME_ZERO = 1670.4
INTEG_TIME = 10    #seconds, per bin
RANDOMIZE  = True
OUTFOLDER  = "./data/"

PLOTMAX = 300 #Upper val of ev scale 

#Delays array
delays = np.arange(-0.1, 0.3, 0.1)

#***************** CODE BEGINS ****************

print(f"Starting {su.bcol.YELLOW}Delay Scan{su.bcol.ENDC} Scan")
print(f"{su.bcol.RED}{su.bcol.BOLD}Is the DAQ running?{su.bcol.ENDC}")
print()

exp = UrsaPQ()
startDate = datetime.now()

#Output array
evs    = exp.data_axis[1]
data = np.zeros((delays.shape[0], evs.shape[0]))

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = su.DataPreview(evs, delays, data, sliceX = ev_slice)

#Generate random permutation
scan_order = np.arange(delays.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)
    
with su.Run('delay') as run_id:
    plot.set_title(f"Delay Scan {run_id}")
    
    for n in scan_order:
        print(f"Scanning delay: {delays[n]:.3f}", end= "\r")
        
        #Set the desired delay stage position 
        su.set_delay(delays[n], TIME_ZERO)
        
        #Reset accumulator for online preview
        exp.data_clearAccumulator = True
        
        #Set up preview updater 
        def updatef():
            diff_data = exp.data_evenAccumulator - exp.data_oddAccumulator
            data[n] = diff_data
            plot.update_data(data)
            
        #Wait for INTEG_TIME while updating the preview
        su.DataPreview.update_wait(updatef, INTEG_TIME)
        
#Setup output folder
from pathlib import Path
Path(OUTFOLDER).mkdir(parents=True, exist_ok=True)
out_fname = f"delay_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}.npz"

#Write out data
np.savez(OUTFOLDER + out_fname, delays=delays, evs=evs, data=data)

print(f"End of scan!")
print(f"Saved file as {out_fname}")














