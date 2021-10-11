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

        One thread reads data from doocs the other processes the data and uploads
        it to clients
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
        self.eTofTrace = None
        self.iTofTrace = None
        
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
        return (oldData * lvl) + (newData * (1-lvl))
        
    def updateTofTraces(self):
        ''' gets new traces from DOOCS, returns True if fetch was successful '''

        # Try pulling new TOF traces from DOOCS
        try:
            new_eTof = self.pydoocs.read(config.Data_DOOCS_eTOF)           
            
            if new_eTof['macropulse'] == self.macropulse: #if we got the same data twice, return false (we dont want to process the same data twice)
                return False
                
            self.macropulse = new_eTof['macropulse'] 

            if config.Data_GmdNorm:
                new_gmd = self.pydoocs.read(config.Data_DOOCS_GMD, 
                                           macropulse = self.macropulse)['data'].T[1]            
            
            new_iTof = self.pydoocs.read(config.Data_DOOCS_iTOF, 
                                           macropulse = self.macropulse)
            
            self.updateFreq = (  0.03 * 1/(new_eTof['timestamp'] - self.timestamp) 
                               + 0.97 * self.updateFreq)
            self.timestamp = new_eTof['timestamp']
        except Exception as error:
            traceback.print_exc()
            return False
            
        if config.Data_Invert:
            new_eTof['data'].T[1] *= -1 
            new_iTof['data'].T[1] *= -1          
                        
        #Two types of online data: Low passed ('moving average') and accumulated
       
        #Low pass:
        #This is run in a separate try...except so that tofTrace gets reinitialized 
        #if the lenght of newTof changes due to DOOCS reconfiguration
        try:
            self.eTofTrace[1]   = self.dataFilter( new_eTof['data'].T[1]   ,  self.eTofTrace[1] )
            self.iTofTrace[1]   = self.dataFilter( new_iTof['data'].T[1]   ,  self.iTofTrace[1] )
        except Exception as error:
            traceback.print_exc()
            self.eTofTrace  = new_eTof['data'].T.copy()
            self.iTofTrace  = new_iTof['data'].T.copy()
                        
        #Accumulate data:
        try:
            self.eTof_accumulator[1] += new_eTof['data'].T[1] 
            self.iTof_accumulator[1] += new_iTof['data'].T[1] 
            self.accumulator_count += 1
            if config.Data_GmdNorm: self.gmd_accumulator += new_gmd.mean()
        except Exception as error:
            traceback.print_exc()
            self.eTof_accumulator  = new_eTof['data'].T.copy() #Rest tof accumulator
            self.iTof_accumulator  = new_iTof['data'].T.copy() #Rest tof accumulator            
            self.accumulator_count = 1
            if config.Data_GmdNorm: self.gmd_accumulator = new_gmd.mean() 
        return True
                          
    def doocsUpdateLoop(self):
        '''
        Keeps reading data from DOOCS and filters it as it comes in.
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            if not self.updateTofTraces():
                continue
               
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
        
    def sliceAverage(self, tofTrace):
        ''' 
            Get a long tof trace, slices it in pieces and returns the 
            average of the even and odd slices.
            Gmd normalization if gmdTrace is given 
        '''
        #Calculate chopping points for slicing
        sliceStartIdx  = np.arange(config.Data_SliceOffset, 
                                    len(tofTrace)-config.Data_SlicePeriod, 
                                   config.Data_SlicePeriod).astype(int)
                         
        stackedTraces = self.stack_slices(tofTrace, sliceStartIdx, config.Data_SliceSize)                      
        
        #Sikp traces
        numTraces = stackedTraces.shape[0]
        start = config.Data_SkipSlices
        end   = numTraces - config.Data_SkipSlicesEnd    
                                 
        bg = np.percentile(stackedTraces, 15, axis=1)
        stackedTraces -= bg[:,None]                                
                                 
        #Sum up all slices skipping the first self.skipSlices
        stacked = stackedTraces[start:end].mean(axis=0)
            
        return stacked, end-start                        
    
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
                eTof_lowPass, traceCount = self.sliceAverage(self.eTofTrace[1])
                iTof_lowPass, traceCount = self.sliceAverage(self.iTofTrace[1])
                
                eTof_acc, traceCount = self.sliceAverage(self.eTof_accumulator[1])
                iTof_acc, traceCount = self.sliceAverage(self.iTof_accumulator[1])                
                
                #slightly thread usafe (as accumulatorCount could be update after sliceAverage returns) 
                #but worst case it's out by 1-2 shots out of hundreds
                eTof_acc /= self.accumulator_count
                iTof_acc /= self.accumulator_count   
                
                if config.Data_GmdNorm:
                    gmd = self.gmd_accumulator / self.accumulator_count
                    eTof_acc /= gmd
                    iTof_acc  /= gmd
                                           
                tofs, evs = self.getTofsAndEvs(self.eTofTrace[0])
                    
                #Output arrays
                self.status.data_axis = np.vstack((tofs, evs))
                self.status.data_eTof_lowPass =  eTof_lowPass
                self.status.data_iTof_lowPass =  iTof_lowPass
                self.status.data_traceNum = traceCount
              
                self.status.data_eTof_acc =  eTof_acc 
                self.status.data_iTof_acc  =  iTof_acc
                self.status.data_AccumulatorCount = self.accumulator_count
               
                self.status.data_updateFreq  = self.updateFreq
                self.status.data_eTofTrace   = self.eTofTrace
                self.status.data_iTofTrace   = self.iTofTrace
                
                if self.status.data_clearAccumulator:
                    # Will throw TypeError in updateTofTraces and reset the accumulators
                    self.accumulator_count = None  
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
