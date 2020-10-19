from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import math
import time
import numpy as np

from config import config
import time


class ursapqDataHandler:
    def __init__(self):
        '''
        Connects to the manager and uploads processed data for online display.
        Data is taken from doocs and processed here for fast display and analysis

        One thread reads data from doocs
        
        Config params:
          "Data_DOOCS_TOF"   : address of tof trace
          "Data_DOOCS_Trig"  : address of trigger trace (not used)
          "Data_DOOCS_GMD"   : addres of GMD
          "Data_DOOCS_LASER" : address of laser trace
          "Data_FilterTau"   : default value for low pass tau,
          "Data_SlicePeriod" : rep rate of FEL in samples (float beacuse FLASH and ADC are not in sync),
          "Data_SliceSize"   : lenght of a single shot tof trace,
          "Data_SliceOffset" : samples to skip before starting slicing (time zero setting),
          "Data_SkipSlices"    : slices to skip at the beginning of each bunch train: must be even,
          "Data_SkipSlicesEnd" : slices to skip at the end of each bunch train: must be even  
          "Data_GmdNorm"       : set to 1 to use gmd normalization (long time trends only, not shot to shot)   
          "Data_Invert"        : set to 1 to invert y axis of data
          "Data_Jacobian"      : set to 1 to use jacobian normalization   
        '''
        
        self.port = config.UrsapqServer_Port
        self.authkey = config.UrsapqServer_AuthKey.encode('ascii')

        #Setup multiprocessing manager
        class statusManager(BaseManager): pass
        statusManager.register('getStatusNamespace', proxytype=NamespaceProxy)
        self.manager = statusManager(('', self.port), self.authkey)

        # Shared system status namespace
        self.manager.connect()
        self.status = self.manager.getStatusNamespace()

        # Init analyis parameters from config file they are not present already
        self.status.data_filterTau = config.Data_FilterTau   # Tau in seconds of the low pass filter on evenShots and oddShots
        self.status.data_clearAccumulator = False            # Flag to signal that user wants an accumulator restart
        
        self.skipSlices     = config.Data_SkipSlices     #How many slices to skip for singleShot average
        self.skipSlicesEnd  = config.Data_SkipSlicesEnd  #How many slices to skip for singleShot average at the end   
        
        if self.skipSlices % 2 != 0 or self.skipSlicesEnd % 2 != 0:
            raise ValueError("skipSlices must be even")
        
        try:
            self.pydoocs = __import__('pydoocs')
        except Exception:
            raise Exception("pydoocs not available")

        self.stopEvent = threading.Event() #Event is set to stop all background threads

        # Data
        self.dataUpdated  = threading.Event() #Event is set every time new data is available
        self.updateFreq = 0
        self.macropulse = 0
        self.timestamp = time.time()
        self.tofTrace = None
        self.laserTrace = None
        self.triggTrace = None
        
    def start(self):
        '''
        Starts Threads to handle incoming data, each thread performs a different
        piece of the analysis
        '''
        self.stopEvent.clear()
        threading.Thread(target = self.doocsUpdateLoop).start()
        threading.Thread(target = self.updateLoop).start()

    def stop(self):
        '''
        Tells background threads to stop
        '''
        self.stopEvent.set()

    def dataFilter(self, newData, oldData):
        '''
        Quick and dirty " Average " filter for incoming data. It's fast and does not
        use memory, while performing almost like a moving average
        '''
        lvl = np.exp( -1 / ( self.status.data_filterTau * self.updateFreq  ))
        return oldData * lvl + newData * (1-lvl)
        
    def updateTofTraces(self):
        ''' gets new traces from DOOCS, returns True if fetch was successful '''
        
        # Try pulling new TOF traces from DOOCS
        try:
            newTof = self.pydoocs.read(config.Data_DOOCS_TOF)
            newLaser = self.pydoocs.read(config.Data_DOOCS_LASER)
            
            if newTof['macropulse'] == self.macropulse: #if we got the same data twice, return false (we dont want to process the same data twice)
                return False
                
            self.macropulse = newTof['macropulse'] 
            
            self.updateFreq = (  0.01 * 1/(newTof['timestamp'] - self.timestamp) 
                               + 0.99 * self.updateFreq)
            self.timestamp = newTof['timestamp']
        except Exception as error:
            traceback.print_exc()
            return False
        
        #Two types of online data: Low passed ('moving average') and accumulated
        
        if config.Data_Invert:
            newTof['data'].T[1] *= -1
        
        #Low pass:
        #This is run in a separate try...except so that tofTrace gets reinitialized 
        #if the lenght of newTof changes due to DOOCS reconfiguration
        try:
            self.tofTrace[1]   = self.dataFilter( newTof['data'].T[1]   ,  self.tofTrace[1] )
        except Exception as error:
            traceback.print_exc()
            self.tofTrace  = newTof['data'].T
            
        #Accumulate data:
        try:
            self.tofAccumulator[1] += newTof['data'].T[1]
            self.tofAccumulatorCount += 1
        except Exception as error:
            traceback.print_exc()
            self.tofAccumulator  = newTof['data'].T  
            self.tofAccumulatorCount = 1
            
        return True
            
    def updateGmd(self):
        #Pull gmd from DOOCS
        try:
            newGmd = self.pydoocs.read(config.Data_DOOCS_GMD, 
                                       macropulse = self.macropulse)['data'].T[1]
        except Exception as error:
            print("Error getting GMD. Check that GMD monitor is active or disable GMD normalization")
            traceback.print_exc()   
            return
            
        # Same as above, try...except to reinitialize if number of shots changes                                                                    
        try:                                              
            self.GMDTrace = self.dataFilter( newGmd  ,  self.GMDTrace )
        except Exception as error:
            traceback.print_exc()
            self.GMDTrace = newGmd
    
    def updateLaserTrace(self):
        try:
            self.laserTrace = self.pydoocs.read(config.Data_DOOCS_LASER, 
                                                macropulse = self.macropulse)['data'].T
        except Exception as error:
            traceback.print_exc()

    def doocsUpdateLoop(self):
        '''
        Keeps reading data from DOOCS and filters it as it comes in.
        The commented part should make it so that it takes in all data sequentially,
        but the ifs slow it down too much.
        '''
        #Run until stop event
        while not self.stopEvent.isSet():

            if not self.updateTofTraces():
                continue
            
            if config.Data_GmdNorm:
                self.updateGmd()
            else:
                self.GMDTrace = None       

            self.updateLaserTrace()
                
            # Notify filter worker that new data is available
            self.dataUpdated.set()
            
    def Tof2eV(self, tof, retard):
        ''' converts time of flight into ectronvolts '''
        # Constants for conversion:
        s = 1.7
        m_over_e = 5.69

        # UNITS AND ORDERS OF MAGNITUDE DO CHECK OUT
        return 0.5 * m_over_e * ( s / tof )**2 - retard

    def stack_slices(self, array, startIdx, sliceLen):
        all_idx = startIdx[:, None] + np.arange(sliceLen)
        return array[all_idx] 
        
    def sliceAverage(self, tofTrace, gmdTrace = None):
        ''' 
            Get a long tof trace, slices it in pieces and returns the 
            average of the even and odd slices.
            Gmd normalization if gmdTrace is given 
        '''
        #Calculate chopping points for slicing
        sliceStartIdx  = np.arange(config.Data_SliceOffset, len(tofTrace), 
                                   config.Data_SlicePeriod).astype(int)
                         
        stackedTraces = self.stack_slices(tofTrace, sliceStartIdx, config.Data_SliceSize)                      
                          
        if gmdTrace is not None:
            raise NotImplementedError("lol")
        else:                        
            #Sum up all slices skipping the first self.skipSlices
            evenSlice = stackedTraces[::2].mean(axis=0)
            oddSlice  = stackedTraces[1::2].mean(axis=0)
            
        return evenSlice, oddSlice                        
    
    def getTofsAndEvs(self, tofAxis):
        #Generate tof times and eV data
        tofs = tofAxis[:config.Data_SliceSize] - tofAxis[0]
                   
        #Generate EV from TOF
        evs = self.Tof2eV( tofs, self.status.tof_retarderHV )    
        return tofs, evs 
             
    def updateLoop(self):
        '''
        Writes incoming data to status namespace. Run in a different thread
        so that doocsUpdateLoop can run as fast as possible
        '''
        #Run until stop event
        while not self.stopEvent.isSet():

            self.dataUpdated.wait()
            self.dataUpdated.clear()
    
            try:       
                evenLowPass, oddLowPass = self.sliceAverage(self.tofTrace[1], self.GMDTrace)
                
                evenAcc, oddAcc = self.sliceAverage(self.tofAccumulator[1], self.GMDTrace)
                evenAcc /= self.tofAccumulatorCount #slightly thread usafe (as tofAccumulatorCount could be update after sliceAverage returns)
                oddAcc  /= self.tofAccumulatorCount #but worst case it's out by 1-2 shots out of hundreds
                       
                tofs, evs = self.getTofsAndEvs(self.tofTrace[0])
                    
                #Output arrays
                self.status.data_axis = np.vstack((tofs, evs))
                self.status.data_evenShots =  evenLowPass
                self.status.data_oddShots  =  oddLowPass
              
                self.status.data_evenAccumulator =  evenAcc 
                self.status.data_oddAccumulator  =  oddAcc
                self.status.data_AccumulatorCount = self.tofAccumulatorCount
               
                self.status.data_updateFreq = self.updateFreq
                self.status.data_laserTrace = self.laserTrace
                self.status.data_tofTrace   = self.tofTrace
                
                if self.status.data_clearAccumulator:
                    self.tofAccumulatorCount = None  # Will throw TypeError in updateTofTraces and reset the accumulator
                    self.status.data_clearAccumulator = False
                                   
            except Exception as e:
                traceback.print_exc()   
                
def main():
    try:
        dataHandler = ursapqDataHandler()
        dataHandler.start()
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        dataHandler.stopEvent.set()

if __name__=='__main__':
    main()
