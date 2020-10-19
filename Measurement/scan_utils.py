import pydoocs
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import time
import numpy as np

DOOCS_RUNID   = 'FLASH.UTIL/STORE/URSAPQ/RUN.ID'
DOOCS_RUNTYPE = 'FLASH.UTIL/STORE/URSAPQ/RUN.TYPE'

DOOCS_DELAY  = 'ASD'
DOOCS_UNDUL  = 'ASD'

runtypes = { 'time_zero'    : 0,
             'delay'        : 1,
             'energy'       : 2,
             'uvPower'      : 3,
             'delay_energy' : 4,
             'other'        : 5 
            }

def set_delay(delay, TIME_ZERO):
    temp_delay = TIME_ZERO - delay
    
def get_delay():
    return temp_delay
    
def set_energy(energy):
    temp_energy = energy
    
def get_energy():
    return temp_energy
    
class Run:
    def __init__(self, runtype):
        try:
            self.type = runtypes[runtype]
        except KeyError as exc:
            raise ValueError("Invalid run type") from exc
            
    def __enter__(self):
        newId = pydoocs.read(DOOCS_RUNID)['data'] + 1
        pydoocs.write(DOOCS_RUNID, newId)
        pydoocs.write(DOOCS_RUNTYPE, self.type)
        return newId
        
    def __exit__(self, type, value, traceback):
        pydoocs.write(DOOCS_RUNTYPE, -1)

class DataPreview:
    def __init__(self, xAx, yAx, data, diff=True, sliceX = None):
        self.sliceX = sliceX
        self.fig = plt.figure()
        self.ax  = self.fig.add_subplot(1, 1, 1)
        self.diff = diff
        
        colormap = 'bwr' if self.diff else 'bone_r'
        self.img = self.ax.pcolormesh(xAx[self.sliceX], yAx, data[:,self.sliceX], shading='nearest', cmap=colormap)
        self.fig.show()
        
    def set_title(self, title):
        self.fig.suptitle(title, fontsize=16)    
        
    def update_data(self, data):
        self.img.set_array(data[:,self.sliceX].ravel())
        
        if self.diff:
            cmax = np.max(np.abs(data[:,self.sliceX]))
            self.img.set_clim(vmin=-cmax, vmax=cmax)
        else:
            cmax = np.max(data[:,self.sliceX])
            self.img.set_clim(vmin=0, vmax=cmax)
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
                    
    #use this method to call update_data() every repTime secs until totTime is elapsed
    @staticmethod
    def update_wait(func, tot_time, rep_time = 2):
        end_time = time.time() + tot_time
        
        while time.time() < end_time:
            func()
            time.sleep(rep_time)
    
    
class bcol:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    ORANGE ='\033[33m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    
    
    
        
