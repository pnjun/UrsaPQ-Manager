from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
import threading

from OvenPS import OvenPS
from Beckhoff import BeckhoffSys
import pyads

from config import config

class UrsapqManager:
    '''
    Keeps track of the status of all components in the setup and syncs the values
    between HW components. Values are then made available to clients trough a
    shared namespace accessible via the ursapqUtils library.

    The updateStatus() function can be used to get info on all tracked values.
    '''

    def __init__(self, port, authkey):
        self.port = port
        self.authkey = authkey

        class statusManager(BaseManager): pass
        statusObj = Namespace()
        statusManager.register('getStatusNamespace', callable = lambda:statusObj, proxytype=NamespaceProxy)
        self.manager = statusManager(('', self.port), self.authkey)

        self.manager.start()
        self.status = self.manager.getStatusNamespace()

        self.beckhoff = BeckhoffSys()
        self.ovenPS = OvenPS()
        self.oven_stop = threading.Event()

    def start(self):
        self.beckhoff.start()

        self.oven_stop.clear()
        self.ovenController()

    def stop(self):
        self.beckhoff.stop()
        self.oven_stop.set()

    #Wrapper functions to make updateStatus func more readable
    #rescale can be provided to process data before writing
    def _beckhoffRead(self, key, name, type, rescale=lambda x:x):
        self.status.__setattr__(key, rescale( self.beckhoff.read(name,type)) )

    def _beckhoffWrite(self, key, name, type):
        try:
            #If __setter variable is present, use its value to update HW
            self.beckhoff.write(name, self.status.__getattr__(key+'__setter'), type)
            #Delete __setter from namespace after
            self.status.__delattr__(key+'__setter')
        except Exception:
            pass
        self.status.__setattr__(key, self.beckhoff.read(name,type))

    def ovenController(self):
        ''' PID filter to control the sample oven temperature '''
        try:
            assert(self.status.oven_isOn)
            self.ovenPS.connect()
            self.status.oven_capVolt  = self.ovenPS[config.Oven_CapChannel].voltage
            self.status.oven_bodyVolt = self.ovenPS[config.Oven_BodyChannel].voltage
            self.status.oven_tipVolt  = self.ovenPS[config.Oven_TipChannel].voltage
            self.status.ovenStatus = "OK"
        except Exception as e:
            self.status.oven_capVolt = float("nan")
            self.status.oven_bodyVolt = float("nan")
            self.status.oven_tipVolt = float("nan")
            self.status.ovenStatus = "ERROR"
            #print(str(e))

        if not self.oven_stop.is_set():
            threading.Timer(config.Oven_ControlPeriod, self.ovenController).start()

    def updateStatus(self, verbose = False):
        #BECKHOFF VALUES

        #Update 'read only' values
        #First argument is variable named exposed by ursapsUtils, second and third are PLC variable names
        self._beckhoffRead('chamberPressure',     'MAIN.Chamber_Pressure',  pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVacPressure',      'MAIN.PreVac_Pressure',   pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVac_OK',           'MAIN.PreVac_OK',         pyads.PLCTYPE_BOOL)
        self._beckhoffRead('mainVac_OK',          'MAIN.MainVac_OK',        pyads.PLCTYPE_BOOL)
        self._beckhoffRead('preVacValve_isOpen',  'MAIN.PreVacValves_Open', pyads.PLCTYPE_BOOL)
        self._beckhoffRead('oven_isOn',           'MAIN.OvenPS_Relay',      pyads.PLCTYPE_BOOL)
        self._beckhoffRead('sample_capTemp',      'MAIN.Sample_CapTemp',    pyads.PLCTYPE_INT,
                            lambda x:x/10)
        self._beckhoffRead('sample_tipTemp',      'MAIN.Sample_TipTemp',    pyads.PLCTYPE_INT,
                            lambda x:x/10)
        self._beckhoffRead('sample_bodyTemp',     'MAIN.Sample_BodyTemp',   pyads.PLCTYPE_INT,
                            lambda x:x/10)

        #Write out config values if necessary + update them after the write attempt
        #Every piece is updating a different variable.
        self._beckhoffWrite('oven_enable',        'MAIN.OvenPS_Enable',      pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('preVacValve_lock',   'MAIN.PreVac_Valve_Lock',  pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('pumps_enable',       'MAIN.Pumps_Enable',       pyads.PLCTYPE_BOOL)

        #If update complete sucessfully, update timestamp
        self.status.lastUpdate = datetime.now()

if __name__=='__main__':
    import time
    expManager = UrsapqManager( config.UrsapqServer_Port , config.UrsapqServer_AuthKey.encode('ascii'))

    while True:
        print("Attempting to start server...")
        try:
            expManager.start()
            print("Server started.")
            while True:
                expManager.updateStatus()
                time.sleep(config.UrsapqServer_UpdatePeriod)

        except Exception as e:
            expManager.stop()
            print("Server Error: %s" % str(e))
        time.sleep(config.UrsapqServer_ReconnectPeriod)
