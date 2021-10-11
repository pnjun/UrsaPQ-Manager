import pydoocs
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import time
import numpy as np

DOOCS_RUNID   = 'FLASH.UTIL/STORE/URSAPQ/RUN.ID'
DOOCS_RUNTYPE = 'FLASH.UTIL/STORE/URSAPQ/RUN.TYPE'
DOOCS_UNDULATOR     = 'FLASH.FEL/UNDULATOR.ML/GROUP.FLASH2/USER.E_PHOTON.SP'
DOOCS_DAQ           = 'TTF2.DAQ/DQM/SVR.FL2USER1/DQMFSTAT'

class RunType:
    time_zero    = 0
    delay        = 1
    energy       = 2
    other        = 100 

    
def set_energy(energy):
    return
    pydoocs.write(DOOCS_UNDULATOR, energy)
    time.sleep(1)  
    

class Run:
    def __init__(self, runtype, skipDAQ = False):
        self.type = runtype
        self.skip = skipDAQ
        
    def __enter__(self):
        if pydoocs.read(DOOCS_DAQ)['data'] != 1 and not  self.skip:
            raise Exception("Start the DAQ, you stupid fuck!")
            
        newId = pydoocs.read(DOOCS_RUNID)['data'] + 1
        pydoocs.write(DOOCS_RUNID, newId)
        pydoocs.write(DOOCS_RUNTYPE, self.type)
                
        return newId
        
    def __exit__(self, exc_type, value, traceback):
        if exc_type:
            pydoocs.write(DOOCS_RUNTYPE, -2) #Exit with error
        else:
            pydoocs.write(DOOCS_RUNTYPE, -1) #Exit finished


class DataPreview:
    def __init__(self, xAx, yAx, data, diff=True, sliceX = None):
        if not sliceX:
            self.sliceX = slice(None, None)
        else:
            self.sliceX = sliceX
        
        self.fig = plt.figure()
        self.fig.canvas.set_window_title('Online Scan Preview')
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
            cmin = np.nanmin(data[:,self.sliceX])
            self.img.set_clim(vmin=cmin, vmax=cmax)
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
                    
    #use this method to call update_data() every repTime secs until totTime is elapsed
    @staticmethod
    def update_wait(func, tot_time, rep_time = 1):
        end_time = time.time() + tot_time
        
        while time.time() < end_time:
            func()
            time.sleep(rep_time)    
    
class TermCol:
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
    
    
    
    
        
