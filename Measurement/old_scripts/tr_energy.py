from scan_utils import *
import numpy as np
import sys
from datetime import datetime, timedelta
import time
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

#**************** SETUP PARAMETERS ************
#Time zero estimate
TIME_ZERO  = -414.3
PARK_DELAY = None

INTEG_TIME = 30    #seconds, per bin
WAVEPLATE  = 27
RETARDER   = 290 
POLARIZ    = 'p'

RANDOMIZE_ENERGY  = True
RANDOMIZE_DELAY   = True

OUTFOLDER  = "./data/"

PLOTROI = (350,420) #Integration region for online plot 

#Delays array
THRD_HARM = True #Use 3rd harmonic of FEL (Sets undulator to 1/3 of energy)
energies    = np.arange(401., 408.1, .5)
#delays      = np.array([0, 1., 1.2])
delaysList      = [np.arange(-0.2, 1.5,.2)]
#delaysList = [np.arange(1, 3.1, .5)]
delays = np.concatenate(delaysList)
                
#***************** CODE BEGINS ****************
time_duration = INTEG_TIME*energies.shape[0]*delays.shape[0]/60 # in minutes
time_duration += energies.shape[0]*delays.shape[0]*(2.5/60)
time_end = str(datetime.now() +timedelta(minutes = time_duration))[:-10]
print(f"Starting {TermCol.YELLOW}{TermCol.BOLD}Time Resolved Energy{TermCol.ENDC} Scan")
#print(f"Time to scan {INTEG_TIME*energies.shape[0]*delays.shape[0]/60} mins")
print(f"Time to scan {time_duration} mins")
print(f"Approximate end: {time_end}") # be here, or you will waste beamtime!
print()

exp = UrsaPQ()
startDate = datetime.now()

exp.tof_retarderSetHV = RETARDER
time.sleep(10)
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
e_idx = np.arange(energies.shape[0])
d_idx = np.arange(delays.shape[0])
if RANDOMIZE_ENERGY:
    e_idx = np.random.permutation(e_idx)
if RANDOMIZE_DELAY:
    d_idx = np.random.permutation(d_idx)

X,Y = np.meshgrid(e_idx,d_idx)
scan_order = np.array([X.flatten(),Y.flatten()]).T

#Setup output folder
from pathlib import Path
Path(OUTFOLDER).mkdir(parents=True, exist_ok=True)

try:
    with Run(RunType.tr_energy, skipDAQ=False) as run_id:
        out_fname = OUTFOLDER + f"trEnergy_{run_id}_{startDate.strftime('%Y.%m.%d-%H.%M')}"
        plot.set_title(f"Run {run_id} - Time Resolved Energy Scan")

        
        
        for e, d in scan_order:
            print(f"Scanning energy {energies[e]:.1f} delay {delays[d]:.3f}", end= "\r")
            
            #Set the desired delay stage position 
            set_energy(energies[e], thrd_harm=THRD_HARM)
            set_delay(delays[d], TIME_ZERO, PARK_DELAY)
            
            #Reset accumulator for online preview
            exp.data_clearAccumulator = True
            
            #Set up preview updater 
            def updatef():
                dataEven[d,e] = exp.data_evenAccumulator
                dataOdd[d,e]  = exp.data_oddAccumulator
                data[d,e]     = (dataEven[d,e] - dataOdd[d,e])[ROI].sum()
                plot.update_data(data)
                
            #Wait for INTEG_TIME while updating the preview
            DataPreview.update_wait(updatef, INTEG_TIME)
            
            #Save partials
            np.savez(out_fname + "_part.npz", energies=energies, delays=delays, evs=evs,  
                                              dataEven=dataEven, dataOdd=dataOdd)
            plot.save_figure(out_fname + "_part.png")
            
except KeyboardInterrupt:
    print()
    print("Scan Stopped")
    interrupted = True
else:
    print()
    print(f"End of scan!")
    interrupted = False

if interrupted:
    out_fname += "_stopped"

#Write out data
np.savez(out_fname + ".npz", energies=energies, delays=delays, evs=evs,  
                             dataEven=dataEven, dataOdd=dataOdd)
plot.save_figure(out_fname + ".png")

print(f"Data saved as {out_fname}")














