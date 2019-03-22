from multiprocessing.managers import BaseManager, NamespaceProxy
from config import config

class UrsaPQ:
    '''
    Provides an interface to the UrsaPQ manager. Instances are connected to a remote manager specified in the constructor parameters (ip address, port and authkey).
    After connection the experimental parameters can be read and set as attributes of the instance. Since parameter setting is done on the remote server, setting attemps might not have immediate effect or might be discarded completelyself.

    Examples:
    exp = UrsaPQ(<IP>, <port>, <authkey>)
    print( exp.ovenEnable ) # prints oven enable status
    exp.ovenEnable = True   # tries to enable oven, might not succeed
                            # check exp.ovenEnable to test

    print( exp.chamberPressure ) # prints chamberPressure
    exp.chamberPressure = 1      # no effect, chamberPressure is read only.

    For a full list of available parameters, see ursapqManager.py or just use:
    print(exp)
    '''

    def __init__(self):
        # Connects to remote manager and obtains an handle on the shared namespace
        # representing the status. (see multiprocessing.Manager)

        class statusManager(BaseManager): pass
        statusManager.register('getStatusNamespace', proxytype=NamespaceProxy)

        super(UrsaPQ, self).__setattr__('_manager', statusManager((config.UrsapqServer_IP,
                                                                   config.UrsapqServer_Port),
                                                                   config.UrsapqServer_AuthKey.encode('ascii')) )
        self._manager.connect()
        super(UrsaPQ, self).__setattr__('_status', self._manager.getStatusNamespace() )

        #if config.WriteDoocs: # if true we write data to doocs
        #    super(UrsaPQ, self).__setattr__('_pydoocs' , __import__('pydoocs'))

        try:
            class writeManager(BaseManager): pass
            writeManager.register('getWriteNamespace', proxytype=NamespaceProxy)

            super(UrsaPQ, self).__setattr__('_writeManager', writeManager((config.UrsapqServer_IP,
                                                                           config.UrsapqServer_WritePort),
                                                                           config.UrsapqServer_WriteKey.encode('ascii')) )
            self._writeManager.connect()
            super(UrsaPQ, self).__setattr__('_writeStatus', self._writeManager.getWriteNamespace() )
        # If writestatus setup fails (missing config?) disable write option
        except Exception:
            super(UrsaPQ, self).__setattr__('_writeStatus', None )

    def __getattr__(self, key):
        # Attribute lookup is passed on directly to the status namespace
        return self._status.__getattr__(key)

    def __setattr__(self, key, val):
        # Attribute setting is done by setting the variable in the writeStatus
        # namespace. expManager process will try to act on that request 
        
        # Attributes named data_* are used for data analysis and can be set directly
        if key.startswith("data_"):
            return self._status.__setattr__(key, val)

        # All other attributes are set on the _writeStatus namespace.
        if self._writeStatus is not None:
            return self._writeStatus.__setattr__(key, val)
        else:
            raise Exception("Writing not allowed, add write password to config file to enable")

    def __repr__(self):
        return str(self._status)

if __name__=='__main__':
    import time
    import matplotlib.pyplot as plt

    ursapq = UrsaPQ()
    print(ursapq.magnet_pos_y)
    
    
