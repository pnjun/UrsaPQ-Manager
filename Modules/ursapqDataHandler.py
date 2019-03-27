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
        try:
            self.pydoocs = __import__('pydoocs')
        except Exception:
            raise Exception("pydoocs not available")

        self.stopEvent = threading.Event() #Event is set to stop all background threads

        # Data
        self.dataUpdated  = threading.Event() #Event is set every time new data is available
        self.updateFreq = 0
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
        threading.Thread(target = self.workerLoop).start()
        threading.Thread(target = self.slicerLoop).start()

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

    #TODO: HANDLE LENGHT CHANGE CASE
    def doocsUpdateLoop(self):
        '''
        Keeps reading data from DOOCS and filters it as it comes in.
        The commented part should make it so that it takes in all data sequentially,
        but the ifs slow it down too much.
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            '''try:
                newTof = self.pydoocs.read(config.Data_DOOCS_TOF, macropulse = self.macropulse + 1)
                newLaser = self.pydoocs.read(config.Data_DOOCS_LASER, macropulse = self.macropulse + 1)
            except Exception: '''
            newTof = self.pydoocs.read(config.Data_DOOCS_TOF)
            newLaser = self.pydoocs.read(config.Data_DOOCS_LASER)
          
            self.macropulse = newTof['macropulse']                 
            try:
                self.updateFreq =  0.01 * 1/(newTof['timestamp'] - self.timestamp) + 0.99 * self.updateFreq
            except Exception:
                pass
            self.timestamp = newTof['timestamp']
            
            try:
                self.tofTrace[1]   = self.dataFilter( newTof['data'].T[1]   ,  self.tofTrace[1] )
            except Exception:
                self.tofTrace  = newTof['data'].T
                
            self.laserTrace = newLaser['data'].T
                
            # Notify filter workers that new data is available
            self.dataUpdated.set()

    def Tof2eV(self, tof, retard):
        ''' converts time of flight into ectronvolts '''
        # Constants for conversion:
        s = 1.7
        m_over_e = 5.69

        # UNITS AND ORDERS OF MAGNITUDE DO CHECK OUT
        return 0.5 * m_over_e * ( s / tof )**2 - retard

    def slicerLoop(self):
        '''
        Sllices self.tofTrace in individual pieces (each piece is a x-ray pulse) and averages
        All slices togheter. Stores result in status.data_tofSingleShot
        '''
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()
            try:
                #Calculate left and right chopping point for slicing
                leftTriggers  = np.arange(self.status.data_sliceOffset,
                                                  len(self.tofTrace[0]), 
                                                  self.status.data_slicePeriod).astype(int)
                                          
                rightTriggers = leftTriggers + self.status.data_sliceSize
                slices = [slice(a,b) for a,b in zip(leftTriggers, rightTriggers)]
                
                if self.status.data_skipSlices % 2 == 0:
                    evenSlices = slices[ self.status.data_skipSlices   :-1:2]
                    oddSlices  = slices[ self.status.data_skipSlices+1 :-1:2]
                else:
                    evenSlices = slices[ self.status.data_skipSlices+1 :-1:2]  
                    oddSlices  = slices[ self.status.data_skipSlices   :-1:2]              
                
                #Sum up all slices skipping the first self.status.data_skipSlices
                evenSlice = np.array(self.tofTrace[1][evenSlices[0]])
                for sl in evenSlices[1:]:
                    evenSlice += self.tofTrace[1][sl]
                evenSlice /= len(slices)
                
                oddSlice = np.array(self.tofTrace[1][oddSlices[0]])
                for sl in oddSlices[1:]:
                    oddSlice += self.tofTrace[1][sl]
                oddSlice /= len(slices)
                
                
                #Generate tof times and eV data
                tofTimes = self.tofTrace[0][slices[self.status.data_skipSlices]] -\
                           self.tofTrace[0][slices[self.status.data_skipSlices].start]
                #Generate EV from TOF
                eV_Times = self.Tof2eV( tofTimes, self.status.tof_retarderHV )

                #Output arrays
                self.status.data_evenShots =  np.vstack((tofTimes, eV_Times, evenSlice ))
                self.status.data_oddShots  =  np.vstack((tofTimes, eV_Times, oddSlice ))
                
            except Exception as e:
                print(e)
 
    def getRisingEdges(self, data, trigger):
        ''' Returns array of indices where a rising edge above trigger value is found in data '''
        return np.flatnonzero((data[:-1] < trigger) & (data[1:] > trigger))
 
    def workerLoop(self):
        '''
        Writes incoming data to status namespace. Run in a different thread
        so that doocsUpdateLoop can run as fast as possible
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()     
           
            #Find time of arrival of first laser pulse
            laserhits = self.getRisingEdges(self.laserTrace[1], 200)
            try:
                self.status.data_laserTime = self.laserTrace[0][laserhits[0]]          
            except Exception:
                self.status.data_laserTime = None
                   
            #Output data to namespace
            self.status.data_updateFreq = self.updateFreq
            self.status.data_laserTrace = self.laserTrace
            self.status.data_tofTrace   = self.tofTrace       

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
