import numpy as np
import matplotlib.pyplot as plt
import sys

file = sys.argv[1]

evRange = (80,120)

d = np.load(file)


evs = d['evs']
waveplate=d['waveplate']

data = d['data'][:, (evs >= evRange[0]) & (evs <= evRange[1])]
integ = np.sum(abs(data), axis=1)

print(type(d['waveplate']))

#holder=[0.02226, 0.03655,0.07712,0.15067,0.20328,0.24761,0.34385,0.40082,0.49703,0.52668,0.59903,0.6804,0.73878]
#holder=[0.02226,0.0308,0.03655,0.05292,0.07712,0.09857,0.15067,0.15909,0.20328,0.21217,0.24761,0.28784,0.34385,0.35744,0.40082,0.4125,0.49703,0.5,0.52668,0.57525,0.59903,0.647,0.6804,0.69185,0.73878,0.76]#,0.81847]
#holder=[0.0308,0.07712,0.15067,0.21217,0.28784,0.40082,0.49703,0.57525,0.647,0.73878,0.81847,0.88006,0.9,0.93,0.95,0.95,0.98]
calib = np.loadtxt("./data/calib400nm.txt")


plt.scatter(calib[:,1]/77, integ)
str1=(str(evRange))
plt.title('Integration range'+str1)
plt.xlabel('Intensity')
plt.show()

#print(d['waveplate'])
#print(integ)



####gubbins
#plt.
#plt.colormesh(evs,delays,data)
#plt.show()
