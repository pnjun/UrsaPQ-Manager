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
        self.status.statusMessage = ""
        self.status.lastStatusMessage = datetime.now()

        self.setMessage("Server is ready, but not started")

    def setMessage(self, msg):
        ''' Sets a server status message that clients can read '''
        self.status.statusMessage = msg
        self.status.lastStatusMessage = datetime.now()

    def start(self):
        self.setMessage("Attempting to start server...")
        self.beckhoff.start()
        self.updateStatus()

        self.controls_stop.clear()
        self.ovenController()

        self.status.tof_hvEnable = False
        self.status.mcp_hvEnable = False
        self.HVPSController()

        self.setMessage("Server started.")

    def stop(self):
        self.setMessage("Server stopped.")
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
        self._beckhoffRead('sample_capTemp',      'MAIN.Sample_CapTemp',    pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_tipTemp',      'MAIN.Sample_TipTemp',    pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_bodyTemp',     'MAIN.Sample_BodyTemp',   pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('magnet_temp',         'MAIN.Magnet_Temp',       pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_posZ','MAIN.SampleZ.NcToPlc.TargetPos',  pyads.PLCTYPE_REAL)

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

        #Write out config values if necessary + update them after the write attempt
        #Every piece is updating a different variable.
        self._beckhoffWrite('oven_enable',        'MAIN.OvenPS_Enable',      pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('preVacValve_lock',   'MAIN.PreVac_Valve_Lock',  pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('pumps_enable',       'MAIN.Pumps_Enable',       pyads.PLCTYPE_BOOL)

        #If update complete sucessfully, update timestamp
        self.status.lastUpdate = datetime.now()

    class OvenOFFException(Exception):
        pass

    #Manages sample oven tempearture control loop
    def ovenController(self):
        ''' PID filter to control the sample oven temperature '''
        try: #try connecting to OVPS, if not,
            if not self.status.oven_isOn:
                raise UrsapqManager.OvenOFFException("Oven PS is off")

            self.ovenPS.connect()
            self.status.oven_capPow  = self.ovenPS.Cap.power
            self.status.oven_bodyPow = self.ovenPS.Body.power
            self.status.oven_tipPow  = self.ovenPS.Tip.power

            self.ovenPS.allOn()
            self.ovenPS.Cap.setVoltage  = self.CapPID.filter(self.status.sample_capTemp)
            self.ovenPS.Tip.setVoltage  = self.TipPID.filter(self.status.sample_tipTemp)
            self.ovenPS.Body.setVoltage = self.BodyPID.filter(self.status.sample_bodyTemp)

            if abs(self.TipPID.lastErr) < config.Oven.PID.NormalOpMaxErr and abs(self.CapPID.lastErr) < config.Oven.PID.NormalOpMaxErr:
                self.status.oven_PIDStatus = "OK"
            else:
                self.status.oven_PIDStatus = "TRACKING"

        except Exception as e:
            self.status.oven_capPow = math.nan
            self.status.oven_bodyPow = math.nan
            self.status.oven_tipPow = math.nan
            self.TipPID.reset()
            self.CapPID.reset()
            self.BodyPID.reset()

            if not self.status.oven_enable:
                self.status.oven_PIDStatus = "OFF"
            else:
                if isinstance(e, UrsapqManager.OvenOFFException):
                    self.setMessage("ERROR: Oven enabled but not active, check interlock")
                else:
                    self.setMessage("ERROR: Cannot connect to OvenPS, check USB")
                    print("OvenPS not reachable: " , traceback.format_exc())
                self.status.oven_PIDStatus = "ERROR"


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
            # HV enable status
            tofEn = self._getParamWrite('tof_hvEnable')
            mcpEn = self._getParamWrite('mcp_hvEnable')
            if tofEn is not None: self.HVPS.tofEnable = tofEn
            if mcpEn is not None: self.HVPS.mcpEnable = mcpEn
            self.status.tof_hvEnable = self.HVPS.tofEnable
            self.status.mcp_hvEnable = self.HVPS.mcpEnable

            self.status.mcp_phosphorHV  = self.HVPS.Phosphor.voltage
            self.status.mcp_backHV      = self.HVPS.Back.voltage
            self.status.mcp_frontHV     = self.HVPS.Front.voltage
            self.status.tof_meshHV      = self.HVPS.Mesh.voltage
            self.status.tof_lensHV      = self.HVPS.Lens.voltage
            self.status.tof_retarderHV  = self.HVPS.Retarder.voltage
            self.status.tof_magnetHV    = self.HVPS.Magnet.voltage

            newMesh     = self._getParamWrite('tof_meshSetHV')
            newLens     = self._getParamWrite('tof_lensSetHV')
            newRetarter = self._getParamWrite('tof_retarderSetHV')
            newMagnet   = self._getParamWrite('tof_magnetSetHV')
            newPhosphor = self._getParamWrite('mcp_phosphorSetHV')
            newBack     = self._getParamWrite('mcp_backSetHV')
            newFront    = self._getParamWrite('mcp_frontSetHV')

            if newMesh     is not None: self.HVPS.Mesh.setVoltage = newMesh
            if newLens     is not None: self.HVPS.Lens.setVoltage = newLens
            if newRetarter is not None: self.HVPS.Retarder.setVoltage = newRetarter
            if newMagnet   is not None: self.HVPS.Magnet.setVoltage = newMagnet
            if newPhosphor is not None: self.HVPS.Phosphor.setVoltage = newPhosphor
            if newBack     is not None: self.HVPS.Back.setVoltage = newBack
            if newFront    is not None: self.HVPS.Front.setVoltage = newFront

            #prevent MCP overvoltage by limiting back-front deltaV
            #Must be done after others have been loaded
            if self.HVPS.Back.setVoltage < self.HVPS.Front.setVoltage:
                self.HVPS.Back.setVoltage = self.HVPS.Front.setVoltage
                self.setMessage("WARNING: MCP Back voltage setpoint rescaled")
            if self.HVPS.Back.setVoltage > self.HVPS.Front.setVoltage + config.HVPS.MaxFrontBackDeltaV:
                self.HVPS.Back.setVoltage = self.HVPS.Front.setVoltage + config.HVPS.MaxFrontBackDeltaV
                self.setMessage("WARNING: MCP Back voltage setpoint rescaled")


            self.status.tof_meshSetHV       = self.HVPS.Mesh.setVoltage
            self.status.tof_lensSetHV       = self.HVPS.Lens.setVoltage
            self.status.tof_retarderSetHV   = self.HVPS.Retarder.setVoltage
            self.status.tof_magnetSetHV     = self.HVPS.Magnet.setVoltage
            self.status.mcp_phosphorSetHV   = self.HVPS.Phosphor.setVoltage
            self.status.mcp_backSetHV       = self.HVPS.Back.setVoltage
            self.status.mcp_frontSetHV      = self.HVPS.Front.setVoltage

            if self.HVPS.tofEnable and self.HVPS.mcpEnable:
                self.status.HV_Status = "OK"
            elif not self.HVPS.tofEnable and not self.HVPS.mcpEnable:
                self.status.HV_Status = "OFF"
            else:
                self.status.HV_Status = "WARNING"

        except Exception:
            self.status.mcp_phosphorHV  = math.nan
            self.status.mcp_backHV      = math.nan
            self.status.mcp_frontHV     = math.nan
            self.status.tof_meshHV      = math.nan
            self.status.tof_lensHV      = math.nan
            self.status.tof_retarderHV  = math.nan
            self.status.tof_magnetHV    = math.nan
            self.status.mcp_phosphorSetHV   = math.nan
            self.status.mcp_backSetHV       = math.nan
            self.status.mcp_frontSetHV      = math.nan
            self.status.tof_meshSetHV       = math.nan
            self.status.tof_lensSetHV       = math.nan
            self.status.tof_retarderSetHV   = math.nan
            self.status.tof_magnetSetHV     = math.nan
            self.status.HV_Status = "ERROR"
            self.setMessage("ERROR: Cannot connect to HVPS, check NIM crate")
            print(traceback.format_exc())

        if self.controls_stop.is_set():
            try:
                self.HVPS.tofEnable = False
                self.HVPS.mcpEnable = False
            except Exception:
                pass
        else:
            threading.Timer(config.HVPS.UpdatePeriod, self.HVPSController).start()

def main():
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

if __name__=='__main__':
    main()
