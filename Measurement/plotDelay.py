import numpy as np
import matplotlib.pyplot as plt
import sys

print("Usage: plotDelay.py <filename>")
print()

INTEGROI = (120,160) #Integration region for online plot 

fin = np.load(sys.argv[1])

data    =  fin['data']
evs     =  fin['evs']
delays  =  fin['delays']


ROI = slice(np.argmin(np.abs(evs - INTEGROI[1])), 
            np.argmin(np.abs(evs - INTEGROI[0])) )
            
data = data[:, ROI]

positive  = np.where( data > 0, data, 0).sum(axis=1)
negavtive = np.where( data < 0, data, 0).sum(axis=1)


plt.plot(delays, positive, label='+')
plt.plot(delays, negavtive, label='-')
plt.legend()
plt.show()
