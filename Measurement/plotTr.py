import numpy as np
import matplotlib.pyplot as plt
import sys

print("Usage: plotTr.py <filename> <delay>")
print()

PLOTROI = (110,170) #Integration region for online plot 

fin = np.load(sys.argv[1])

dataEven =  fin['dataEven']
dataOdd =   fin['dataOdd']
energies =  fin['energies']
delays =    fin['delays']
evs    =    fin['evs']
 

ROI = slice(np.argmin(np.abs(evs - PLOTROI[1])), 
            np.argmin(np.abs(evs - PLOTROI[0])) )

delIdx = np.abs( np.float(sys.argv[2]) - delays ).argmin()
diff = dataEven[delIdx] - dataOdd[delIdx]

diff = diff[:,ROI]
evs  = evs[ROI]


cmax = np.abs( np.max( diff ))
plt.pcolormesh(evs, energies, diff, cmap='bwr', vmin = -cmax, vmax=cmax, shading='nearest')

plt.show()
