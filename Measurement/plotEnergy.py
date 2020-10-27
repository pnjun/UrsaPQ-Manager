import numpy as np
import matplotlib.pyplot as plt
import sys

print("Usage: plotEnergy.py <filename>")
print()

INTEGROI = (10,60) #Integration region for online plot 

fin = np.load(sys.argv[1])

dataEven    =  fin['dataEven']
dataOdd     =  fin['dataOdd']
evs         =  fin['evs']
energies    =  fin['energies']


ROI = slice(np.argmin(np.abs(evs - INTEGROI[1])), 
            np.argmin(np.abs(evs - INTEGROI[0])) )
            
            
            
data = dataEven[:, ROI] - dataOdd[:, ROI]
evs  = evs[ROI]

positive  = np.where( data > 0, data, 0).sum(axis=1)
negavtive = np.where( data < 0, data, 0).sum(axis=1)


plt.plot(energies, positive, label='+')
plt.plot(energies, negavtive, label='-')

plt.legend()
plt.show()
