import numpy as np
import matplotlib.pyplot as plt
import sys


filename = "./data/trEnergy_123_2022.12.17-01.54.npz"  #"./data/trEnergy_121_2022.12.16-22.17.npz"

fin = np.load(filename)

dataEven =  fin['dataEven']
dataOdd =   fin['dataOdd']
evs    =    fin['evs']
energ = fin["energies"]
delay = fin["delays"]


dim1, dim2, _ = dataOdd.shape
diff = dataEven - dataOdd

roi = [200,270] #in ev
bins_of_interest = np.array([(evs>roi[0]) * (evs < roi[1])])[0]


integral = np.sum(diff[:,:,bins_of_interest],axis=2)


    

fig,ax = plt.subplots(num="plot_integral")

x = energ
y = delay
dmax = np.nanmax(abs(integral))
ax.pcolormesh(x,y, integral,cmap = "RdBu", vmin=-dmax, vmax=dmax)
ax.set_xlabel("energy in eV")
ax.set_ylabel("delay in ps")
plt.show()
