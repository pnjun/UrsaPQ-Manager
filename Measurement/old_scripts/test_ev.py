import numpy as np
import matplotlib.pyplot as plt
import sys


filename = "./data/trEnergy_123_2022.12.17-01.54.npz"  #"./data/trEnergy_121_2022.12.16-22.17.npz"

fin = np.load(filename)

dataEven =  fin['dataEven']
dataOdd =   fin['dataOdd']
evs    =    fin['evs']

fig,ax = plt.subplots(num="test")


ax.plot(evs,dataEven[5,10,:])
ax.set_xlim(0,600)
plt.show()
