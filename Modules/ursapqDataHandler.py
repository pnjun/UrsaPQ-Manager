from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import math
import time

from config import config
import time


class ursapqDataHandler:
    def __init__(self):
        '''
        Connects to the manager and uploads processed data for online display.
        Data is taken from doocs and processed here for fast display and analysis
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

        #If config is set, initialize DOOCS communication
        self.doocs = config.UrsapqServer_WriteDoocs # if true we write data to doo
        if self.doocs:
            self.pydoocs = __import__('pydoocs')
            self.doocs_stop = threading.Event() # Stops event for DOOCS update thread


def main():
    dataHandler = ursapqDataHandler()


if __name__=='__main__':
    main()
