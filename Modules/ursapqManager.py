from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import time

from OvenPS import OvenPS
from Beckhoff import BeckhoffSys
import pyads
from config import config


class TempPIDFilter:
    def __init__(self, p, i ,d, setPoint):
        '''
        Temperature PID filter. Takes the filter coefficients for the
        proportional, integral and derivative components
        '''
        self.d = d
        self.i = i
        self.p = p
        self.setPoint = setPoint
        self.reset()

    def filter(self, t_in):
        if not self.lastcall:
            self.lastcall = datetime.now()
        now = datetime.now()

        dt = (now - self.lastcall).total_seconds() #get time elapsed since last filter run
        err = self.setPoint - t_in

        self.integ += dt*err
        out = self.p * err + self.i * self.integ + self.d / dt * (err - self.lastErr)
        self.lastErr = err
        self.lastcall = now

        return out

    def reset(self):
        self.integ = 0
        self.lastErr = 0
        self.lastcall = None


class UrsapqManager:
    '''
    Keeps track of the status of all components in the setup and syncs the values
    between HW components. Values are then made available to clients trough a
    shared namespace accessible via the ursapqUtils library.

    The updateStatus() and ovenController() functions can be used to get info on all tracked values.
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

        self.TipPID =  TempPIDFilter(*tuple(config.Oven_TipPIDParams),  config.Oven_TipDefSetpoint)
        self.CapPID =  TempPIDFilter(*tuple(config.Oven_CapPIDParams),  config.Oven_CapDefSetpoint)
        self.BodyPID = TempPIDFilter(*tuple(config.Oven_BodyPIDParams), config.Oven_BodyDefSetpoint)

    def start(self):
        self.beckhoff.start()
        self.updateStatus()

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

        self._beckhoffRead('sample_posZ','MAIN.SampleZ.NcToPlc.TargetPos', pyads.PLCTYPE_REAL)

        #Write out config values if necessary + update them after the write attempt
        #Every piece is updating a different variable.
        self._beckhoffWrite('oven_enable',        'MAIN.OvenPS_Enable',      pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('preVacValve_lock',   'MAIN.PreVac_Valve_Lock',  pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('pumps_enable',       'MAIN.Pumps_Enable',       pyads.PLCTYPE_BOOL)

        #If update complete sucessfully, update timestamp
        self.status.lastUpdate = datetime.now()

    def ovenController(self):
        ''' PID filter to control the sample oven temperature '''
        try:
            assert(self.status.oven_isOn)
            self.ovenPS.connect()
            self.status.oven_capPow  = self.ovenPS[config.Oven_CapCh].power
            self.status.oven_bodyPow = self.ovenPS[config.Oven_BodyCh].power
            self.status.oven_tipPow  = self.ovenPS[config.Oven_TipCh].power
        except Exception:
            self.status.oven_capPow = float("nan")
            self.status.oven_bodyPow = float("nan")
            self.status.oven_tipPow = float("nan")

            self.TipPID.reset()
            self.CapPID.reset()
            self.BodyPID.reset()
            self.status.oven_PIDStatus = "OFF"
            #print(traceback.format_exc())
        else:
            self.ovenPS.allOn()
            self.ovenPS[config.Oven_CapCh].setVoltage  = self.CapPID.filter(self.status.sample_capTemp)
            self.ovenPS[config.Oven_TipCh].setVoltage  = self.TipPID.filter(self.status.sample_tipTemp)
            self.ovenPS[config.Oven_BodyCh].setVoltage = self.BodyPID.filter(self.status.sample_bodyTemp)

            print(abs(self.TipPID.lastErr))

            if abs(self.TipPID.lastErr) < config.Oven_NormalOpMaxErr:
                self.status.oven_PIDStatus = "OK"
            else:
                self.status.oven_PIDStatus = "TRACKING"

        if self.oven_stop.is_set():
            self.ovenPS.allOff()
            self.TipPID.reset()
            self.CapPID.reset()
            self.BodyPID.reset()
        else:
            threading.Timer(config.Oven_ControlPeriod, self.ovenController).start()

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
            print("Server Error:")
            print(traceback.format_exc())
        time.sleep(config.UrsapqServer_ReconnectPeriod)
