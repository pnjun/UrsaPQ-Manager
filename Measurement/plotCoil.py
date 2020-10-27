import numpy as np
import matplotlib.pyplot as plt
import glob

PLOTROI = (80,115)

#run_nums = np.arange(273, 289, 1)
run_nums = np.concatenate([[289 ,290, 291], np.arange(277, 289, 1)])
currents = np.arange(100, 850, 50)


data = []

for num in run_nums:
    fname = glob.glob(f"data/coil_{num}*.npz")
    npz = np.load(fname[0])
    data.append( npz['data'] )

evs  = npz['evs']
ROI = slice(np.argmin(np.abs(evs - PLOTROI[1])), 
            np.argmin(np.abs(evs - PLOTROI[0])) )


data = np.array(data)[:, ROI]
evs  = evs[ROI]

plt.figure()
for n, trace in enumerate(data):
    plt.plot(evs, trace + 10*n, label=f"{currents[n]} mA")

plt.legend()


plt.figure()

data /= np.linalg.norm(data, axis=1)[:,None]

pos = np.where(data > 0, data, 0).sum(axis=1)
neg = np.where(data < 0, data, 0).sum(axis=1)

plt.plot(currents, pos, label='norm + area')
plt.plot(currents, -neg, label='norm - area')
plt.legend()
plt.show()

            

