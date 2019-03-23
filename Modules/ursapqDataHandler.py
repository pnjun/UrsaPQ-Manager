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
        self.tofTrace = None
        self.laserTrace = None
        self.triggTrace = None
        
        self.macropulse = None
        self.timestamp = 0

    def start(self):
        '''
        Starts Threads to handle incoming data, each thread performs a different
        piece of the analysis
        '''
        self.stopEvent.clear()
        threading.Thread(target = self.doocsUpdateLoop).start()
        threading.Thread(target = self.workerLoop).start()
        #threading.Thread(target = self.slicerLoop).start()

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
        return oldData * self.status.data_filterLvl + newData * (1-self.status.data_filterLvl)

    #TODO: HANDLE LENGHT CHANGE CASE
    def doocsUpdateLoop(self):
        '''
        Keeps reading data from DOOCS and filters it as it comes in.
        The commented part should make it so that it takes in all data sequentially,
        but the ifs slow it down too much. Might need to rewrite it with try...except
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            '''try:
                assert(time.time() - self.timestamp > 0.5)
                self.newTof = self.pydoocs.read(config.Data_FLASH_TOF, macropulse = self.macropulse + 1)
                self.newLaser = self.pydoocs.read(config.Data_DOOCS_LASER, macropulse = self.macropulse + 1)
            except Exception: 

                print("skip")'''
                
            self.newTof = self.pydoocs.read(config.Data_DOOCS_TOF)
            self.newLaser = self.pydoocs.read(config.Data_DOOCS_LASER)
           
            self.macropulse = self.newTof['macropulse']
            self.timestamp  = self.newTof['timestamp']
            
            try:
                #assert(newTof['data'].T.shape == self.tofTrace.shape) #IF shape changed, reinit variables
                self.tofTrace[1]   = self.dataFilter( self.newTof['data'].T[1]   ,  self.tofTrace[1] )
                self.laserTrace[1] = self.dataFilter( self.newLaser['data'].T[1] ,  self.laserTrace[1] )

            except TypeError:
                self.tofTrace  = self.newTof['data'].T
                self.laserTrace = self.newLaser['data'].T
                
            # Notify filter workers that new data is available
            self.dataUpdated.set()

    def getRisingEdges(self, data, trigger):
        ''' Returns array of indices where a rising edge above trigger value is found in data '''
        return np.flatnonzero((data[:-1] < trigger) & (data[1:] > trigger))

    def slicerLoop(self):
        '''
        Sllices self.tofTrace in individual pieces (each piece is a x-ray pulse) and averages
        All slices togheter. Stores result in status.data_tofSingleShot
        '''
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()

            leftTriggers  = np.int( np.arange(self.status.data_sliceOffset, 
                                              len(self.tofTrace[0]), 
                                              self.status.data_slicePeriod) )
                                      
            rightTriggers = leftTriggers + self.status.data_sliceSize
            slices = [slice(a,b) for a,b in zip(leftTriggers, rightTriggers)]

            
            #Sum up all slices skipping the first self.status.data_skipSlices
            tofSlice = np.array(self.tofTrace[1][slices[self.status.data_skipSlices]])
            
            for sl in slices[self.status.data_skipSlices+1:]:
                tofSlice += self.tofTrace[1][sl]

            #Create output array with averaged sliced data and translated time axis values
            self.status.data_tofSingleShot = np.vstack( tofSlice / len(slices), 
                                                        self.tofTrace[0][slices[0]] - 
                                                        self.tofTrace[0][slices[0].start] )
 

    def Tof2eV(self, tof, retard):
        ''' converts time of flight into ectronvolts '''
        # Constants for conversion:
        s = 1.7
        m_over_e = 5.69

        # UNITS AND ORDERS OF MAGNITUDE DO CHECK OUT
        return 0.5 * m_over_e * ( s / tof )**2 - retard

    def workerLoop(self):
        '''
        Writes incoming data to status namespace. Run in a different thread
        so that doocsUpdateLoop can run as fast as possible
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()     
            #Generate EV from TOF
            #ev_x = self.Tof2eV( self.tofTrace[0] - self.status.data_timeZero, self.status.tof_retarderHV )
            print(self.macropulse)
           
            #Output data to namespace
            self.status.data_laserTrace = self.laserTrace
            self.status.data_tofTrace   = self.tofTrace       
            #self.status.data_tofEv = ev_x

def main():
    while True:
        try:
            dataHandler = ursapqDataHandler()
            dataHandler.start()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            dataHandler.stopEvent.set()
            exit()

if __name__=='__main__':
    main()
