from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import matplotlib.pyplot as plt
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
        self.status.data_filterLvl = config.Data_FilterLevel
        self.status.data_sliceSize = config.Data_SliceSize
        self.status.data_sliceOffset = config.Data_SliceOffset

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
        threading.Thread(target = self.statusUpdateLoop).start()
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
            # If we are running behind doocs, drop data by jumping ahaead
            '''if time.time() - self.timestamp > 0.5:
                self.macropulse = None

            # If macropulse is none, get newest available data
            if not self.macropulse:
                newTof = self.pydoocs.read(config.Data_FLASH_TOF)
            else:
                newTof = self.pydoocs.read(config.Data_FLASH_TOF, macropulse = self.macropulse + 1)'''

            newTof = self.pydoocs.read(config.Data_DOOCS_TOF)
            newLaser = self.pydoocs.read(config.Data_DOOCS_LASER)
            newTrigg = self.pydoocs.read(config.Data_DOOCS_Trig)
            
            self.macropulse = newTof['macropulse']
            self.timestamp  = newTof['timestamp']

            try:
                #assert(newTof['data'].T.shape == self.tofTrace.shape) #IF shape changed, reinit variables
                self.tofTrace[1]   = self.dataFilter( newTof['data'].T[1]   ,  self.tofTrace[1] )
                self.laserTrace[1] = self.dataFilter( newLaser['data'].T[1] ,  self.laserTrace[1] )
                #self.triggTrace[1] = self.dataFilter( newTrigg['data'].T[1] ,  self.triggTrace[1] )
            except TypeError:
                self.tofTrace  = newTof['data'].T
                self.laserTrace = newLaser['data'].T
            
            self.triggTrace = newTrigg['data'].T
                
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
            triggers = self.getRisingEdges(self.triggTrace[1], config.Data_TriggerVal)

            leftTriggers  = triggers +  self.status.data_sliceOffset
            rightTriggers = triggers +  self.status.data_sliceOffset + self.status.data_sliceSize
            slices = [slice(a,b) for a,b in zip(leftTriggers, rightTriggers)]

            try:
                tofSlice = np.array(self.tofTrace[1][slices[0]])
                for sl in slices[1:-1]:
                    tofSlice += self.tofTrace[1][sl]

                self.status.data_tofSingleShot = tofSlice / len(slices)
            except IndexError:
                print("No trigger for slicing")
                self.status.data_tofSingleShot = None

    def statusUpdateLoop(self):
        '''
        Writes incoming (filtered) data to status namespace. Run in a different thread
        so that doocsUpdateLoop can run as fast as possible
        '''
        #Run until stop event
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()
            self.status.data_laserTrace = self.laserTrace
            self.status.data_tofTrace   = self.tofTrace

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
