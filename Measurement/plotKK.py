import numpy as np
import matplotlib.pyplot as plt
import sys

print("Usage: plotKK.py <filename> <delay>")
print()

KK_START = -35 #Ev, with respect to the photoline position
KK_END   = -2  #Ev, with respect to the photoline position

fin = np.load(sys.argv[1])

dataEven =  fin['dataEven']
dataOdd  =   fin['dataOdd']
energies =  fin['energies']
evs    =    fin['evs']

kk_evn = []
kk_odd = []

try:
    delays =    fin['delays']
    delIdx = np.abs( np.float(sys.argv[2]) - delays ).argmin()
    
    dataEven = dataEven[delIdx]
    dataOdd  = dataOdd[delIdx]
except Exception:
    print("No time resolved data in file, continuing...")
    

for n, en in enumerate(energies):
    photoIdx = np.argmax(dataOdd[n])
    photoEn  = evs[photoIdx]

    ROI = slice(np.argmin(np.abs(evs - (photoEn + KK_END) )), 
                np.argmin(np.abs(evs - (photoEn + KK_START) )) )
                
    kk_evn.append( dataEven[n,ROI].sum() )
    kk_odd.append( dataOdd[n,ROI].sum()  )          


kk_odd = np.array(kk_odd)
kk_evn = np.array(kk_evn)

plt.plot(energies, kk_odd, label="KK integral odd")
plt.plot(energies, kk_evn, label="KK integral even")
plt.plot(energies, kk_evn - kk_odd, label="diff")
plt.legend()
plt.show()
