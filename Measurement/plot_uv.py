import numpy as np
import matplotlib.pyplot as plt

file = './data/uvPower_54_2022.12.15-08.02.npz'

evRange = (10,35)

d = np.load(file)


evs = d['evs']

data = d['data'][:, (evs >= evRange[0]) & (evs <= evRange[1])]
integ = np.sum(abs(data), axis=1)

print(type(d['waveplate']))

#plt.scatter(d['waveplate'], integ)
#str1=(str(evRange))
#str2=(str(evRange[1]))
#plt.title('Integration range'+str1)
#plt.show()

#print(d['waveplate'])
#print(integ)



####gubbins
#plt.
