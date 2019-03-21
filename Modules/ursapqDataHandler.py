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

        try:
            self.pydoocs = __import__('pydoocs')
        except Exception:
            raise Exception("pydoocs not available")

        self.stopEvent = threading.Event() #Event is set to stop all background threads

        # Data
        self.dataUpdated  = threading.Event() #Event is set every time new data is available
        self.tofTrace = None
        self.macropulse = None
        self.timestamp = 0

    def start(self):
        self.stopEvent.clear()
        threading.Thread(target = self.doocsUpdateLoop).start()
        threading.Thread(target = self.statusUpdateLoop).start()
        threading.Thread(target = self.slicerLoop).start()

    def stop(self):
        self.stopEvent.set()

    def dataFilter(self, newData, oldData):
        return oldData * config.Data_FilterLevel + newData * (1-config.Data_FilterLevel)

    #TODO: HANDLE LENGHT CHANGE CASE
    def doocsUpdateLoop(self):
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

            newTof = self.pydoocs.read(config.Data_FLASH_TOF)

            self.macropulse = newTof['macropulse']
            self.timestamp  = newTof['timestamp']

            try:
                #self.tofTrace[0] = newTof['data'][:][0]
                self.tofTrace[1] = self.dataFilter( newTof['data'].T[1] ,  self.tofTrace[1] )
            except TypeError:
                self.tofTrace  = newTof['data'].T

            # Notify filter workers that new data is available
            self.dataUpdated.set()

    def getRisingEdges(self, data, trigger):
        ''' Returns array of indices where a rising edge above trigger value is found. '''
        return np.flatnonzero((data[:-1] < trigger) & (data[1:] > trigger))

    def slicerLoop(self):
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()
            triggers = self.getRisingEdges(self.tofTrace[1], config.Data_TriggerLevel)

            leftTriggers  = triggers + config.Data_TriggerOffset
            rightTriggers = triggers + config.Data_TriggerOffset + config.Data_TriggerWindow
            slices = [slice(a,b) for a,b in zip(leftTriggers, rightTriggers)]

            tofSlice = np.array(self.tofTrace[1][slices[0]])
            for sl in slices[1:]:
                tofSlice += self.tofTrace[1][sl]

            self.status.data_tofSingleShot = tofSlice / len(slices)

    def statusUpdateLoop(self):
        #Run until stop event
        while not self.stopEvent.isSet():
            self.dataUpdated.wait()
            self.status.data_tofTrace = self.tofTrace

def main():
    dataHandler = ursapqDataHandler()
    try:
        dataHandler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dataHandler.stopEvent.set()
        exit()

if __name__=='__main__':
    main()
