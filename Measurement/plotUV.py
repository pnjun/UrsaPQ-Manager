import numpy as np
import matplotlib.pyplot as plt
import sys

print("Usage: plotUV.py <filename>")
print()

PLOTROI = (120,160) #Integration region for online plot 

fin = np.load(sys.argv[1])

data =  fin['data']
evs  =  fin['evs']
wp   =  fin['waveplate']


ROI = slice(np.argmin(np.abs(evs - PLOTROI[1])), 
            np.argmin(np.abs(evs - PLOTROI[0])) )
            
data = data[:, ROI]

positive  = np.where( data > 0, data, 0).sum(axis=1)
negavtive = np.where( data < 0, data, 0).sum(axis=1)


plt.plot(wp, positive)
plt.plot(wp, negavtive)
plt.show()
