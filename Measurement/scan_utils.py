import pydoocs
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import time
import numpy as np

DOOCS_RUNID   = 'FLASH.UTIL/STORE/URSAPQ/RUN.ID'
DOOCS_RUNTYPE = 'FLASH.UTIL/STORE/URSAPQ/RUN.TYPE'
DOOCS_DELAY_SET  = 'FLASH.SYNC/LASER.LOCK.EXP/FLASH2.PPL1.OSC1/FMC0.MD22.0.POSITION_SET.WR'
DOOCS_DELAY_GET  = 'FLASH.SYNC/LASER.LOCK.EXP/FLASH2.PPL1.OSC1/FMC0.MD22.0.POSITION.RD'
DOOCS_UNDUL  = 'ASD'

DELAY_DRIVE_WAIT_TIME  = 1  # How long to wait for motor to move after setting delay
DELAY_PARK_WAIT_TIME   = 2  # How long to wait for motor to move into parking position


runtypes = { 'time_zero'    : 0,
             'delay'        : 1,
             'energy'       : 2,
             'uvPower'      : 3,
             'delay_energy' : 4,
             'other'        : 5 
            }

def set_delay(delay, time_zero = None, park_position=None):
    if park_position:
        pydoocs.write(DOOCS_DELAY_SET, park_position)     
        time.sleep(DELAY_PARK_WAIT_TIME)

    if time_zero:
        new_delay = time_zero - delay 
    else:
        new_delay = delay
        
    pydoocs.write(DOOCS_DELAY_SET, new_delay)
    time.sleep(DELAY_DRIVE_WAIT_TIME)
    
def get_delay():
    return pydoocs.read(DOOCS_DELAY_GET)['data']
    
def set_energy(energy):
    #TODO
    pass
    
def get_energy():
    #TODO
    pass
    
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
    
    def save_figure(self, fname):
        self.fig.savefig(fname, dpi=1200)
        
    def update_data(self, data):
        self.img.set_array(data[:,self.sliceX].ravel())
        
        if self.diff:
            cmax = np.nanmax(np.abs(data[:,self.sliceX]))
            self.img.set_clim(vmin=-cmax, vmax=cmax)
        else:
            cmax = np.nanmax(data[:,self.sliceX])
            self.img.set_clim(vmin=0, vmax=cmax)
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
                    
    #use this method to call update_data() every repTime secs until totTime is elapsed
    @staticmethod
    def update_wait(func, tot_time, rep_time = 1):
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
    
    
    
    
        
