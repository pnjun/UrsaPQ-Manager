from multiprocessing.managers import BaseManager, NamespaceProxy

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

    def __init__(self, ipAddr, port, authkey):
        # Connects to remote manager and obtains an handle on the shared namespace
        # representing the status. (see multiprocessing.Manager)
        class statusManager(BaseManager): pass
        statusManager.register('getStatusNamespace', proxytype=NamespaceProxy)

        super(UrsaPQ, self).__setattr__('_manager', statusManager((ipAddr, port), authkey) )
        self._manager.connect()
        super(UrsaPQ, self).__setattr__('_status', self._manager.getStatusNamespace() )

    def __getattr__(self, key):
        # Attribute lookup is passed on directly to the status namespace
        return self._status.__getattr__(key)

    def __setattr__(self, key, val):
        # Attribute setting is done by setting the key__setter variable in the
        # status namespace. expManager process will try to act on that request.
        if key.endswith('__setter'):
            raise Exception("Variable names ending with '__setter' are reserved")

        return self._status.__setattr__(key + '__setter', val)

    def __repr__(self):
        return str(self._status)

if __name__=='__main__':
    import time
    ursapq = UrsaPQ( '192.168.0.0' , 2222 , 'ursapqManager_TurboOK'.encode('ascii'))
    print(ursapq.lastUpdate)
    print(ursapq.preVacPressure)
    print( ursapq.sample_pos_x )

