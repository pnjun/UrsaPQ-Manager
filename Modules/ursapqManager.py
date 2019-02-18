from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import math
import time

from OvenPS import OvenPS
from HVPS import HVPS
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

        # Applied power scales with square of voltage. Since the filters outputs a voltage we sqrt
        # the PID out to make it linear in applied power.
        return math.sqrt(abs(out))

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
        self.HVPS = HVPS()
        self.controls_stop = threading.Event() # Stops background event loops (oven and HVPS controllers)

        self.TipPID =  TempPIDFilter(*tuple(config.Oven.PID.TipParams),  config.Oven.PID.TipDefSetpoint)
        self.CapPID =  TempPIDFilter(*tuple(config.Oven.PID.CapParams),  config.Oven.PID.CapDefSetpoint)
        self.BodyPID = TempPIDFilter(*tuple(config.Oven.PID.BodyParams), config.Oven.PID.BodyDefSetpoint)

    def start(self):
        self.beckhoff.start()
        self.updateStatus()

        self.controls_stop.clear()
        self.ovenController()

        self.status.hv_tofEnable = False
        self.status.hv_mcpEnable = False
        self.HVPSController()

    def stop(self):
        self.beckhoff.stop()
        self.controls_stop.set()

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

    def _getParamWrite(self, key):
        ''' Checks if a paramater write request has been made by a client. If so, returns the value and deletes
            the request. Returns none otherwise '''
        try:
            var = self.status.__getattr__(key + '__setter')
            self.status.__delattr__(key+'__setter')
            return var
        except:
            return None

    def updateStatus(self, verbose = False):
        #BECKHOFF VALUES

        #Update 'read only' values
        #First argument is variable named exposed by ursapsUtils, second and third are PLC variable names
        self._beckhoffRead('chamberPressure',     'MAIN.Chamber_Pressure',  pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVacPressure',      'MAIN.PreVac_Pressure',   pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVac_OK',           'MAIN.PreVac_OK',         pyads.PLCTYPE_BOOL)
        self._beckhoffRead('mainVac_OK',          'MAIN.MainVac_OK',        pyads.PLCTYPE_BOOL)
        self._beckhoffRead('pumps_areON',         'MAIN.TurboPump_ON',      pyads.PLCTYPE_BOOL)
        self._beckhoffRead('preVacValve_isOpen',  'MAIN.PreVacValves_Open', pyads.PLCTYPE_BOOL)
        self._beckhoffRead('oven_isOn',           'MAIN.OvenPS_Relay',      pyads.PLCTYPE_BOOL)
        self._beckhoffRead('sample_capTemp',      'MAIN.Sample_CapTemp',    pyads.PLCTYPE_INT,
                            lambda x:x/10)
        self._beckhoffRead('sample_tipTemp',      'MAIN.Sample_TipTemp',    pyads.PLCTYPE_INT,
                            lambda x:x/10)
        self._beckhoffRead('sample_bodyTemp',     'MAIN.Sample_BodyTemp',   pyads.PLCTYPE_INT,
                            lambda x:x/10)
        self._beckhoffRead('sample_posZ','MAIN.SampleZ.NcToPlc.TargetPos', pyads.PLCTYPE_REAL)

        # Update PID setpoints if necessary
        newTip = self._getParamWrite('oven_tipSetPoint')
        newCap = self._getParamWrite('oven_capSetPoint')
        newBody = self._getParamWrite('oven_bodySetPoint')
        if newTip is not None: self.TipPID.setPoint = newTip
        if newCap is not None: self.CapPID.setPoint = newCap
        if newBody is not None: self.BodyPID.setPoint = newBody
        self.status.oven_tipSetPoint = self.TipPID.setPoint
        self.status.oven_capSetPoint = self.CapPID.setPoint
        self.status.oven_bodySetPoint = self.BodyPID.setPoint

        # HV enable status
        tofEn = self._getParamWrite('hv_tofEnable')
        mcpEn = self._getParamWrite('hv_mcpEnable')
        if tofEn != None: self.status.hv_tofEnable = tofEn
        if mcpEn != None: self.status.hv_mcpEnable = mcpEn

        #Write out config values if necessary + update them after the write attempt
        #Every piece is updating a different variable.
        self._beckhoffWrite('oven_enable',        'MAIN.OvenPS_Enable',      pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('preVacValve_lock',   'MAIN.PreVac_Valve_Lock',  pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('pumps_enable',       'MAIN.Pumps_Enable',       pyads.PLCTYPE_BOOL)

        #If update complete sucessfully, update timestamp
        self.status.lastUpdate = datetime.now()

    #Manages sample oven tempearture control loop
    def ovenController(self):
        ''' PID filter to control the sample oven temperature '''
        try: #try connecting to OVPS, if not,
            assert(self.status.oven_isOn)
            self.ovenPS.connect()
            self.status.oven_capPow  = self.ovenPS.Cap.power
            self.status.oven_bodyPow = self.ovenPS.Body.power
            self.status.oven_tipPow  = self.ovenPS.Tip.power

            self.ovenPS.allOn()
            self.ovenPS.Cap.setVoltage  = self.CapPID.filter(self.status.sample_capTemp)
            self.ovenPS.Tip.setVoltage  = self.TipPID.filter(self.status.sample_tipTemp)
            self.ovenPS.Body.setVoltage = self.BodyPID.filter(self.status.sample_bodyTemp)

            if abs(self.TipPID.lastErr) < config.Oven_NormalOpMaxErr and abs(self.CapPID.lastErr) < config.Oven_NormalOpMaxErr:
                self.status.oven_PIDStatus = "OK"
            else:
                self.status.oven_PIDStatus = "TRACKING"
        except Exception:
            self.status.oven_capPow = math.nan
            self.status.oven_bodyPow = math.nan
            self.status.oven_tipPow = math.nan

            self.TipPID.reset()
            self.CapPID.reset()
            self.BodyPID.reset()
            self.status.oven_PIDStatus = "OFF"
            #print(traceback.format_exc())

        if self.controls_stop.is_set():
            self.ovenPS.allOff()
            self.TipPID.reset()
            self.CapPID.reset()
            self.BodyPID.reset()
        else:
            threading.Timer(config.Oven.ControlPeriod, self.ovenController).start()

    #Manages HVPS, runs separately from main update function due to serial not updating fast enough
    def HVPSController(self):
        ''' Manages serial comms with HVPSs '''
        try:
            self.HVPS.connect()
            self.HVPS.tofEnable = self.status.hv_tofEnable
            self.HVPS.mcpEnable = self.status.hv_mcpEnable

            self.status.hv_phosphor  = self.HVPS.Phosphor.voltage
            self.status.hv_back      = self.HVPS.Back.voltage
            self.status.hv_front     = self.HVPS.Front.voltage
            self.status.hv_mesh      = self.HVPS.Mesh.voltage
            self.status.hv_lens      = self.HVPS.Lens.voltage

            newPhosphor = self._getParamWrite('hv_setPhosphor')
            newMesh     = self._getParamWrite('hv_setMesh')
            newLens     = self._getParamWrite('hv_setLens')
            newBack     = self._getParamWrite('hv_setBack')
            newFront    = self._getParamWrite('hv_setFront')

            if newPhosphor is not None: self.HVPS.Phosphor.setVoltage = newPhosphor
            if newMesh     is not None: self.HVPS.Mesh.setVoltage = newMesh
            if newLens     is not None: self.HVPS.Lens.setVoltage = newLens
            if newBack     is not None: self.HVPS.Back.setVoltage = newBack
            #prevent MCP overvoltage by limiting back-front deltaV
            if newFront is not None:
                newFront = min( newFront, self.HVPS.Back.setVoltage + config.HVPS.MaxFrontBackDeltaV)
                self.HVPS.Front.setVoltage = newFront

            self.status.hv_setPhosphor   = self.HVPS.Phosphor.setVoltage
            self.status.hv_setMesh       = self.HVPS.Mesh.setVoltage
            self.status.hv_setLens       = self.HVPS.Lens.setVoltage
            self.status.hv_setBack       = self.HVPS.Back.setVoltage
            self.status.hv_setFront      = self.HVPS.Front.setVoltage

            if self.HVPS.tofEnable and self.HVPS.mcpEnable:
                self.status.HVPS_Status = "OK"
            elif not self.HVPS.tofEnable and not self.HVPS.mcpEnable:
                self.status.HVPS_Status = "OFF"
            else:
                self.status.HVPS_Status = "WARNING"

        except Exception:
            self.status.hv_phosphor  = math.nan
            self.status.hv_back      = math.nan
            self.status.hv_front     = math.nan
            self.status.hv_mesh      = math.nan
            self.status.hv_lens      = math.nan
            self.status.hv_setPhosphor   = math.nan
            self.status.hv_setMesh       = math.nan
            self.status.hv_setLens       = math.nan
            self.status.hv_setBack       = math.nan
            self.status.hv_setFront      = math.nan
            self.status.HVPS_Status = "ERROR"
            print(traceback.format_exc())

        if self.controls_stop.is_set():
            try:
                self.HVPS.tofEnable = False
                self.HVPS.mcpEnable = False
            except Exception:
                pass
        else:
            threading.Timer(config.HVPS.UpdatePeriod, self.HVPSController).start()


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
