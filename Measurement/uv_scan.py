from scan_utils import *
import numpy as np
import sys
from datetime import datetime
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
TIME_ZERO = 1456.6

INTEG_TIME = 25    #seconds, per bin
DELAY      = 2     #ps
RETARDER = 20 
POLARIZ    = 's'

RANDOMIZE  = True

OUTFOLDER  = "./data/"
PLOTMAX  = 300 #Upper val of ev scale 


#Delays array
waveplate = np.arange(0., 45.1, 2)

#***************** CODE BEGINS ****************

print(f"Starting {TermCol.YELLOW}UV Power{TermCol.ENDC} Scan")
print(f"{TermCol.RED}{TermCol.BOLD}Is the DAQ running?{TermCol.ENDC}")
print(f"Time to scan {INTEG_TIME*waveplate.shape[0]/60} mins")
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
set_delay(DELAY, TIME_ZERO)
set_polarization(POLARIZ)

#Output array
#NaN initialization in case scan is stopped before all data is acquired
evs      = exp.data_axis[1]
data = np.empty((waveplate.shape[0], evs.shape[0]))
data[:] = np.NaN

#Setup preview window
ev_slice = slice(np.abs( evs - PLOTMAX ).argmin(), None) #Range of ev to plot
plot = DataPreview(evs, waveplate, data, sliceX = ev_slice)

#Generate random permutation
scan_order = np.arange(waveplate.shape[0])
if RANDOMIZE:
    scan_order = np.random.permutation(scan_order)

try:
    with Run(RunType.uvPower) as run_id:
        plot.set_title(f"Run {run_id} - UV Power Scan")
        
        for n in scan_order:
            print(f"Scanning waveplate: {waveplate[n]:.1f}", end= "\r")
            
            #Set the desired delay stage position 
            set_waveplate(waveplate[n])
            
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
out_fname = OUTFOLDER + f"uvPower_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", waveplate=waveplate, evs=evs, data=data)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














