#!/usr/bin/python

from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import math
import time
import numpy as np
import pydoocs as pds

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
        self.skipSlicesEnd  = config.Data_SkipSlices     #How many slices to skip for singleShot average at the end   
        
        if self.skipSlices % 2 != 0 or self.skipSlicesEnd % 2 != 0:
            raise ValueError("skipSlices must be even")

        self.stopEvent = threading.Event() #Event is set to stop all background threads

        # Data
        self.dataUpdated  = threading.Event() #Event is set every time new data is available
        self.updateFreq = 0
        self.macropulse = 0
        self.timestamp = time.time()
        self.tofTrace = None
        self.gmd = None #Rate of gmd in uJ / s, filtered
        self.laserTrace = np.empty((2,2)) #empty data for when laser trace cannot be read from DOOCS
        self.triggTrace = None
        
    def start(self):
        '''
        Starts Threads to handle incoming data, each thread performs a different
        piece of the analysis
        '''
        self.stopEvent.clear()
        pds.connect([config.Data_DOOCS_TOF], cycles=-1)
        threading.Thread(target = self.doocsUpdateLoop).start()
        threading.Thread(target = self.updateLoop).start()

        self.tof_trace_daq_len = pds.read(config.Data_DOOCS_TOF_LEN)['data'] #Get set value for TRACE->DAQ lenght

    def stop(self):
        '''
        Tells background threads to stop
        '''
        self.stopEvent.set()
        pds.disconnect()

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
            zmqdata = pds.getdata()
            if zmqdata is None:
                return False

            newTof = zmqdata[0]    
            newGmd = pds.read(config.Data_DOOCS_GMD, macropulse = newTof['macropulse'])   

            self.macropulse = newTof['macropulse']
            self.updateFreq = (  0.03 * 1/(newTof['timestamp'] - self.timestamp) 
                               + 0.97 * self.updateFreq)
            self.timestamp = newTof['timestamp']
            
        except Exception as error:
            traceback.print_exc()
            return False
        
        #CHOP trace so that it maches DAQ:
        newTof['data'] = newTof['data'][:self.tof_trace_daq_len,:]

        if config.Data_Invert:
            newTof['data'][:,1] *= -1      
        newGmd['data'] = newGmd['data'][config.Data_SkipSlices:config.Data_ShotNum]
                
        #Two types of online data: Low passed ('moving average') and accumulated
       
        #Low pass:
        #This is run in a separate try...except so that tofTrace gets reinitialized 
        #if the lenght of newTof changes due to DOOCS reconfiguration
        try:
            self.tofTrace[1]   = self.dataFilter( newTof['data'][:,1]   ,  self.tofTrace[1] )
            self.gmd        = self.dataFilter(newGmd['data'][:,1], self.gmd) 
        except Exception as error:
            traceback.print_exc()
            self.tofTrace  = newTof['data'].T.copy()
            self.gmd = newGmd['data'][:,1].copy()

        #Accumulate data:
        try:
            self.tof_accumulator[1] += newTof['data'][:,1] 
            self.accumulatorCount += 1
            self.gmd_even_accum += newGmd['data'][::2,1].sum()
            self.gmd_odd_accum  += newGmd['data'][1::2,1].sum()
        except Exception as error:
            traceback.print_exc()
            self.tof_accumulator  = newTof['data'].T.copy() #Rest tof accumulator
            self.accumulatorCount = 1
            self.gmd_even_accum = newGmd['data'][::2,1].sum()
            self.gmd_odd_accum  = newGmd['data'][1::2,1].sum()
        return True
                           
    def updateLaserTrace(self):
        try:
            self.laserTrace = pds.read(config.Data_DOOCS_LASER, 
                                                macropulse = self.macropulse)['data'].T                 
        except Exception as error:
            traceback.print_exc()

    def doocsUpdateLoop(self):
        '''
        Keeps reading data from DOOCS and filters it as it comes in.
        '''
        #Run until stop event
        while not self.stopEvent.is_set():
            if not self.updateTofTraces():
                continue
            if config.Data_ReadLaser:
                self.updateLaserTrace()
            # Notify filter worker that new data is available
            self.dataUpdated.set()
            
    def Tof2eV(self, tof, retard):
        ''' converts time of flight into ectronvolts '''
        # Constants for conversion:
        s = config.Data_BottleLenght
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
        end   = config.Data_ShotNum    
                                 
        bg = np.percentile(stackedTraces, 10, axis=1)
        stackedTraces -= bg[:,None]                                
                                 
        #Sum up all slices skipping the first self.skipSlices
        evenSlice = stackedTraces[start:end:2]
        oddSlice  = stackedTraces[start+1:end:2]
        assert evenSlice.shape == oddSlice.shape, f"Check slicing config, unequal number of even and odd slices"
        assert evenSlice.shape[0] == self.gmd.size/2, f"GMD shot number does not match slices number"

        return evenSlice.mean(axis=0), oddSlice.mean(axis=0), end-start                        
    
    def getTofsAndEvs(self, tofAxis):
        #Generate tof times and eV data
        tofs = tofAxis[:config.Data_SliceSize] - tofAxis[0]

        #avoid 0tof, leads to +inf eV
        tofs += config.Data_eTof_start

        #Generate EV from TOF
        evs = self.Tof2eV( tofs, self.status.tof_retarderHV )    
        return tofs, evs 
             
    def updateLoop(self):
        '''
        Writes incoming data to status namespace. Run in a different thread
        so that doocsUpdateLoop can run as fast as possible
        '''
        #Run until stop event
        while not self.stopEvent.is_set():
            self.dataUpdated.wait()
            self.dataUpdated.clear()
    
            try:       
                evenLowPass, oddLowPass, traceCount = self.sliceAverage(self.tofTrace[1])
                evenAcc, oddAcc, traceCount = self.sliceAverage(self.tof_accumulator[1])

                #slightly thread usafe (as accumulatorCount / gmd could be updated after sliceAverage returns)
                #but worst case it's out by 1-2 shots out of hundreds
                if config.Data_GmdNorm:
                    evenAcc /= self.gmd_even_accum
                    oddAcc  /= self.gmd_odd_accum

                    evenLowPass /= self.gmd[::2].sum()
                    oddLowPass /= self.gmd[1::2].sum()
                else:
                    evenAcc /= self.accumulatorCount
                    oddAcc  /= self.accumulatorCount                      
                                           
                tofs, evs = self.getTofsAndEvs(self.tofTrace[0])
                    
                #Output arrays
                self.status.data_axis = np.vstack((tofs, evs))
                self.status.data_evenShots =  evenLowPass
                self.status.data_oddShots  =  oddLowPass
                self.status.data_traceNum = traceCount
                self.status.gmd_rate = self.gmd[:].sum() * 10 # 10 shots per second. gmd_rate is total GMD per second

                self.status.data_evenAccumulator =  evenAcc 
                self.status.data_oddAccumulator  =  oddAcc
                self.status.data_AccumulatorCount = self.accumulatorCount
                self.status.data_gmdAccumulator  = self.gmd_even_accum + self.gmd_odd_accum
                self.status.data_updateFreq = self.updateFreq
                self.status.data_laserTrace = self.laserTrace
                self.status.data_tofTrace   = self.tofTrace
                
                if self.status.data_clearAccumulator:
                    # Will throw TypeError in updateTofTraces and reset the accumulators
                    self.accumulatorCount = None  
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
