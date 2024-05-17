
from multiprocessing.managers import BaseManager, Namespace, NamespaceProxy
from datetime import datetime
from collections import namedtuple
import threading
import traceback
import math
import time
import serial

from PID import PIDFilter
from HVPS import HVPS
from LVPS import LVPS
from Beckhoff import BeckhoffSys
import pyads
from config import config
import time

class UrsapqManager:
    '''
    Keeps track of the status of all components in the setup and syncs the values
    between HW components. Values are then made available to clients trough a
    shared namespace ( self.status ) accessible via the ursapqUtils library.
    The shared namespace is implemented using the multiprocessing.Manager python lib.
    It also takes care communication with DOOCS.

    The updateStatus(), ovenController() and HVPSController() functions can be used to get info on all tracked values.

    The control is split in various threads with different tasks (one thread per task):
        * Beckhoff readout
        * Oven Temperature control
        * HV power supply control
        * DOOCS update

    The start() and stop() functions are used to start and stop the data update loops.
    The multiprocessing managers is always active.
    '''
    def __init__(self):
        '''
        Creates the namespace and starts the multiprocessing manager.
        Initializes hardware control moudles and PID filters for oven control
        '''

        # Status namespace for client to read
        self.port = config.UrsapqServer_Port
        self.authkey = config.UrsapqServer_AuthKey.encode('ascii')

        class statusManager(BaseManager): pass
        statusObj = Namespace()
        statusManager.register('getStatusNamespace', callable = lambda:statusObj, proxytype=NamespaceProxy)
        self.manager = statusManager(('', self.port), self.authkey)

        self.manager.start()
        self.status = self.manager.getStatusNamespace()

        # Namespace for client write requests
        self.writePort = config.UrsapqServer_WritePort
        self.writeKey = config.UrsapqServer_WriteKey.encode('ascii')

        class writeManager(BaseManager): pass
        writeRequestObj = Namespace()
        writeManager.register('getWriteNamespace', callable = lambda:writeRequestObj, proxytype=NamespaceProxy)
        self.writeManager = writeManager(('', self.writePort), self.writeKey)

        self.writeManager.start()
        self.writeStatus = self.writeManager.getWriteNamespace()

        # Instances of hardware control modules
        self.beckhoff = BeckhoffSys()
        self.LVPS = LVPS()
        self.HVPS = HVPS()

        self.controls_stop = threading.Event()  # Stops event for control threads of oven and HVPS controllers

        #PID filters
        self.OvenPID =  PIDFilter(**config.OvenPID.init_params._asdict())
        self.PressurePID =  PIDFilter(**config.PressurePID.init_params._asdict())

        #System status message initalization
        self.status.statusMessage = ""
        self.status.lastStatusMessage = datetime.now()

        #If config is set, initialize DOOCS communication
        self.doocs = config.UrsapqServer_WriteDoocs # if true we write data to doo
        if self.doocs:
            self.pydoocs = __import__('pydoocs')
            self.doocs_stop = threading.Event() # Stops event for DOOCS update thread

        self.setMessage("Server is ready, but not started")

    def setMessage(self, msg, timeout = None):
        '''
        Sets a server status message that clients can read.
        If timeout is specified, message goes back to previous message after timeout
        '''

        if False: # Not working properly, TO BE FIXED
            old_message = self.status.statusMessage
            threading.Timer(timeout, self.setMessage, ["ASDF Running", None] ).start()

        print(f"Server Message: {msg}")
        self.status.statusMessage = msg
        self.status.lastStatusMessage = datetime.now()


    def start(self):
        ''' Starts status update operations. '''
        self.setMessage("Attempting to start server...")
        self.beckhoff.start()

        self.status.coil_current = math.nan
        self.status.coil_setCurrent = math.nan
        self.status.oven_output_pow = math.nan
        self.status.coil_wiggle_ampl = 0
        self.status.coil_wiggle_freq = 0
        self.status.coil_current_set = 0
        self.status.oven_enable = False

        self.updateStatus()

        self.controls_stop.clear()
        self.LVPSController()
        self.HVPSController()

        if self.doocs:
            self.doocs_stop.clear()
            self.writeDoocs()

        self.setMessage("Server running")

    def stop(self):
        ''' Stops status update operations. '''
        self.beckhoff.stop()
        self.controls_stop.set()

        if self.doocs:
            self.doocs_stop.set()

        self.setMessage("Server stopped")

    #Wrapper functions to make updateStatus func more readable
    #rescale can be provided to process data before writing
    def _beckhoffRead(self, key, name, type, rescale=lambda x:x):
        self.status.__setattr__(key, rescale( self.beckhoff.read(name,type)) )

    def _beckhoffWrite(self, key, name, type):
        try:
            #If __setter variable is present, use its value to update HW
            self.beckhoff.write(name, self.writeStatus.__getattr__(key), type)
            #Delete __setter from namespace after
            self.writeStatus.__delattr__(key)
        except Exception:
            pass
        self.status.__setattr__(key, self.beckhoff.read(name,type))

    #Wrapper function to make processing of write requests from clients cleaner
    def _getParamWrite(self, key):
        ''' Checks if a paramater write request has been made by a client. If so, returns the value and deletes
            the request. Returns none otherwise '''
        try:
            var = self.writeStatus.__getattr__(key)
            self.writeStatus.__delattr__(key)
            return var
        except:
            return None

    def writeDoocs(self):
        ''' Writes values to DOOCS '''

        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/PRESSURE.CHAMBER", self.status.chamberPressure)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/PRESSURE.PREVAC",  self.status.preVacPressure)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/PRESSURE.GASLINE", self.status.gasLine_pressure)

        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/MCP.PHOSPHORHV", self.status.mcp_phosphorHV)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/MCP.BACKHV",     self.status.mcp_backHV)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/MCP.FRONTHV",    self.status.mcp_frontHV)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/TOF.MESHHV",     self.status.tof_meshHV) #MESH DOES NOT EXIST
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/TOF.LENSHV",     self.status.tof_middleHV)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/TOF.RETARDERHV", self.status.tof_retarderHV)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/TOF.MAGNETHV",   math.nan)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.CAPTEMP",      self.status.sample_capTemp)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.TIPTEMP",      self.status.sample_tipTemp)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.BODYTEMP",     self.status.sample_bodyTemp)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.GASFLOW",      self.status.gasLine_flow)

        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/MAGNET.TEMP", self.status.magnet_temp)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.POSX", self.status.sample_pos_x)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.POSY", self.status.sample_pos_y)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/SAMPLE.POSZ", self.status.sample_pos_z)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/MAGNET.POSY", self.status.magnet_pos_y)
        
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/COIL.CURRENT", self.status.coil_current)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/COIL.AMPLITUDE", self.status.coil_wiggle_ampl)
        self.pydoocs.write("FLASH.UTIL/STORE/URSAPQ/COIL.FREQUENCY", self.status.coil_wiggle_freq)



        if not self.doocs_stop.is_set():
            threading.Timer(config.UrsapqServer_DoocsUpdatePeriod, self.writeDoocs).start()

    def updateStatus(self, verbose = False):
        '''
        Main update function. Reads/Writes values from beckhoff to the status namespace and
        updates the oven temperature set points if needed.
        '''

        #Update 'read only' values
        #First argument is variable named exposed by ursapsUtils, second and third are PLC variable names
        self._beckhoffRead('chamberPressure',     'MAIN.Chamber_Pressure',  pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVacPressure',      'MAIN.PreVac_Pressure',   pyads.PLCTYPE_REAL)
        self._beckhoffRead('preVac_OK',           'MAIN.PreVac_OK',         pyads.PLCTYPE_BOOL)
        self._beckhoffRead('mainVac_OK',          'MAIN.MainVac_OK',        pyads.PLCTYPE_BOOL)
        self._beckhoffRead('pumps_areON',         'MAIN.TurboPump_ON',      pyads.PLCTYPE_BOOL)
        self._beckhoffRead('pumps_normalOp',      'MAIN.Turbo_NO',          pyads.PLCTYPE_BOOL)
        self._beckhoffRead('pump_speed',          'MAIN.TurboMain_Freq',    pyads.PLCTYPE_UINT)
        self._beckhoffRead('preVacValve_isOpen',  'MAIN.PreVacValves_Open', pyads.PLCTYPE_BOOL)
        self._beckhoffRead('LVPS_isOn',           'MAIN.LVPS_ON',      pyads.PLCTYPE_BOOL)
        self._beckhoffRead('sample_capTemp',      'MAIN.Sample_CapTemp',    pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_tipTemp',      'MAIN.Sample_TipTemp',    pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_bodyTemp',     'MAIN.Sample_BodyTemp',   pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('magnet_temp',         'MAIN.Magnet_Temp',       pyads.PLCTYPE_INT, lambda x:x/10)
        self._beckhoffRead('sample_pos_x',   'MAIN.SampleX.NcToPlc.ActPos', pyads.PLCTYPE_LREAL)
        self._beckhoffRead('sample_pos_y',   'MAIN.SampleY.NcToPlc.ActPos', pyads.PLCTYPE_LREAL)
        self._beckhoffRead('sample_pos_z',   'MAIN.SampleZ.NcToPlc.ActPos', pyads.PLCTYPE_LREAL)
        self._beckhoffRead('magnet_pos_y',   'MAIN.MagnetY.NcToPlc.ActPos', pyads.PLCTYPE_LREAL)
        self._beckhoffRead('gasLine_flow',     'MAIN.Sample_Flow',  pyads.PLCTYPE_REAL)
        self._beckhoffRead('gasLine_pressure', 'MAIN.GasLine_Pressure',  pyads.PLCTYPE_REAL)
        self._beckhoffRead('gasLine_enable', 'MAIN.GasLine_Enable',  pyads.PLCTYPE_BOOL)
        self._beckhoffRead('coil_enable',    'MAIN.Coil_Enable',  pyads.PLCTYPE_BOOL)
        self._beckhoffRead('coil_current',   'MAIN.Coil_Curr_In', pyads.PLCTYPE_INT)

        # Coil wiggle
        newWiggleAmpl = self._getParamWrite('coil_wiggle_ampl')
        if newWiggleAmpl is not None: self.status.coil_wiggle_ampl = newWiggleAmpl

        newWiggleFreq = self._getParamWrite('coil_wiggle_freq')
        if newWiggleFreq is not None: self.status.coil_wiggle_freq = newWiggleFreq

        newCurrent = self._getParamWrite('coil_current_set')
        if newCurrent is not None: self.status.coil_current_set = newCurrent

        wiggle = self.status.coil_wiggle_ampl/2*math.sin(self.status.coil_wiggle_freq*2*math.pi*time.time()) #Wiggle component
        self.beckhoff.write("MAIN.Coil_Curr_Out", int(self.status.coil_current_set + wiggle), pyads.PLCTYPE_INT)

        # Oven/Pressure PIDs
        oven_enable = self._getParamWrite('oven_enable')
        if oven_enable is not None: self.status.oven_enable = oven_enable

        newOvenTemp = self._getParamWrite('oven_setPoint')
        if newOvenTemp is not None: self.OvenPID.setPoint = newOvenTemp
        self.status.oven_setPoint = self.OvenPID.setPoint

        newPressureSetP = self._getParamWrite('pressurePID_setPoint')
        if newPressureSetP is not None: self.PressurePID.setPoint = min(newPressureSetP, config.PressurePID.max_setp)
        self.status.pressurePID_setPoint = self.PressurePID.setPoint

        if self.status.gasLine_enable:
            self.writeStatus.gasLine_flow_set = self.PressurePID.filter(self.status.chamberPressure)
        else:
            self.writeStatus.gasLine_flow_set = 0
            self.PressurePID.reset()

        # Check if a client requested a change and wirte it out to beckhoff if necessary
        # self.status namespace values are updated to the new value if write is succesful
        self._beckhoffWrite('gasLine_enable',     'MAIN.GasLine_Enable',      pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('light_enable',       'MAIN.Lamp1_Enable',       pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('preVacValve_lock',   'MAIN.PreVac_Valve_Lock',  pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('pumps_enable',       'MAIN.Pumps_Enable',       pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_x_setPoint',   'MAIN.SampleX_SetPoint', pyads.PLCTYPE_REAL)
        self._beckhoffWrite('sample_pos_y_setPoint',   'MAIN.SampleY_SetPoint', pyads.PLCTYPE_REAL)
        self._beckhoffWrite('sample_pos_z_setPoint',   'MAIN.SampleZ_SetPoint', pyads.PLCTYPE_REAL)
        self._beckhoffWrite('sample_pos_x_enable',     'MAIN.SampleX_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_y_enable',     'MAIN.SampleY_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_z_enable',     'MAIN.SampleZ_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_x_stop',       'MAIN.SampleX_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_y_stop',       'MAIN.SampleY_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('sample_pos_z_stop',       'MAIN.SampleZ_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('magnet_pos_y_setPoint',   'MAIN.MagnetY_SetPoint', pyads.PLCTYPE_REAL)
        self._beckhoffWrite('magnet_pos_y_enable',     'MAIN.MagnetY_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('magnet_pos_y_stop',       'MAIN.MagnetY_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('frame_pos_x_setPoint',    'MAIN.FrameX_SetPoint',  pyads.PLCTYPE_REAL)
        self._beckhoffWrite('frame_pos_y_setPoint',    'MAIN.FrameY_SetPoint',  pyads.PLCTYPE_REAL)
        self._beckhoffWrite('frame_pos_x_enable',      'MAIN.FrameX_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('frame_pos_y_enable',      'MAIN.FrameY_MotionEnable', pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('frame_pos_x_stop',        'MAIN.FrameX_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('frame_pos_y_stop',        'MAIN.FrameY_MotionStop',   pyads.PLCTYPE_BOOL)
        self._beckhoffWrite('gasLine_flow_set',        'MAIN.Sample_Flow_Set',  pyads.PLCTYPE_REAL)
        self._beckhoffWrite('coil_enable',             'MAIN.Coil_Enable',  pyads.PLCTYPE_BOOL)

        #If update complete sucessfully, update timestamp
        self.status.lastUpdate = datetime.now()

    #Manages sample oven tempearture control loop
    def LVPSController(self):
        '''
        Runs the PID filter for oven control and sets coil current
        Attempts connection with the hardware and updates values if possible.
        Values are set to NaN if no hardware connection fails.
        If update succeeded, new voltages are calculated via the PID filters
        '''

        if self.status.LVPS_isOn: # no point in trying if power is off
            try:
                self.LVPS.connect()

                if self.status.oven_enable:
                    self.LVPS.Oven.on()
                    # Applied power scales with square of voltage. Since the filters outputs a voltage we sqrt
                    # the PID out to make it linear in applied power.
                    self.LVPS.Oven.setVoltage  = math.sqrt(self.OvenPID.filter(self.status.sample_bodyTemp))

                    # Write oven status variable
                    if self.OvenPID.lastErr is not None and abs(self.OvenPID.lastErr) < config.OvenPID.NormalOpMaxErr:
                        self.status.oven_PIDStatus = "OK"
                    else:
                        self.status.oven_PIDStatus = "TRACKING"
                else:
                    self.LVPS.Oven.off()
                    self.OvenPID.reset()
                    self.status.oven_PIDStatus = "OFF"

                self.status.oven_output_pow  = self.LVPS.Oven.power

            # If connection failed, set everything to NaN and reset PID filters
            except Exception as e:
                try:
                    self.LVPS.allOff()
                except serial.serialutil.SerialException:
                    pass
                
                self.LVPS.close()
                self.OvenPID.reset()

                self.status.oven_output_pow = math.nan

                self.setMessage("ERROR: Cannot connect to LVPS, check USB", 5)
                print("LVPS not reachable: " , traceback.format_exc())     
                
        else: #LVPS is off
            if self.status.oven_enable:
                self.status.oven_PIDStatus = "ERROR"
                self.setMessage("WARNING: LVPS disabled, cannot run oven (overtemp/overpressure?)", 5)
            else:
                self.status.oven_PIDStatus = "OFF"
                

        # If stopping, switch everything off and reset PID filters
        if self.controls_stop.is_set():
            try:
                self.LVPS.allOff()
            except serial.serialutil.SerialException:
                pass
            self.LVPS.close()
            self.OvenPID.reset()
        # If not stopping, calls itself again after configurable interval
        else:
            threading.Timer(config.LVPS.ControlPeriod, self.LVPSController).start()

    def HVPSController(self):
        '''
        Manages serial comms with HVPSs.
        Reqires different (longer) update period than the main update since serial communication is slow.
        If communication with HVPS is possible, updates the values. If not sets everything to NaN.

        WARNING: In order to let users switch channles on/off manually through the buttons on the PS,
        channels are only turned on/off programmatically when the enable status changes. If a user
        turns channles on/off manually, an inconsistent state is created, as the enable status will not reflect
        the real channel status.
        '''
        try:
            # Try connecting
            self.HVPS.connect()

            # Check if user has changed the enable status and acts on it
            tofEn = self._getParamWrite('tof_hvEnable')
            mcpEn = self._getParamWrite('mcp_hvEnable')
            if tofEn is not None: self.HVPS.tofEnable = tofEn
            if mcpEn is not None: self.HVPS.mcpEnable = mcpEn
            # Updates enable value if enable is succesful
            self.status.tof_hvEnable = self.HVPS.tofEnable
            self.status.mcp_hvEnable = self.HVPS.mcpEnable

            # Update actual voltages
            self.status.mcp_phosphorHV  = self.HVPS.Phosphor.voltage
            self.status.mcp_backHV      = self.HVPS.Back.voltage
            self.status.mcp_frontHV     = self.HVPS.Front.voltage
            self.status.tof_middleHV    = self.HVPS.Middle.voltage
            self.status.tof_retarderHV  = self.HVPS.Retarder.voltage
            self.status.tof_meshHV      = self.HVPS.Mesh.voltage
            
            
            # Read in write requests for voltage setpoints
            newMiddle     = self._getParamWrite('tof_middleSetHV')
            newRetarter   = self._getParamWrite('tof_retarderSetHV')
            newMesh       = self._getParamWrite('tof_meshSetHV')
            newPhosphor = self._getParamWrite('mcp_phosphorSetHV')
            newBack     = self._getParamWrite('mcp_backSetHV')
            newFront    = self._getParamWrite('mcp_frontSetHV')

            # Apply new setpoints if needed
            if newMiddle     is not None: self.HVPS.Middle.setVoltage = newMiddle
            if newRetarter   is not None: self.HVPS.Retarder.setVoltage = newRetarter
            if newMesh       is not None: self.HVPS.Mesh.setVoltage = newMesh
            
            if newPhosphor is not None: self.HVPS.Phosphor.setVoltage = newPhosphor
            if newBack     is not None: self.HVPS.Back.setVoltage = newBack
            if newFront    is not None: self.HVPS.Front.setVoltage = newFront

            #prevent MCP overvoltage by limiting back-front deltaV
            #Must be done after others setpoints have been loaded
            if self.HVPS.Back.setVoltage < self.HVPS.Front.setVoltage:
                self.HVPS.Back.setVoltage = self.HVPS.Front.setVoltage
                self.setMessage("WARNING: MCP Back voltage setpoint rescaled", 30)
            if self.HVPS.Back.setVoltage > self.HVPS.Front.setVoltage + config.HVPS.MaxFrontBackDeltaV:
                self.HVPS.Back.setVoltage = self.HVPS.Front.setVoltage + config.HVPS.MaxFrontBackDeltaV
                self.setMessage("WARNING: MCP Back voltage setpoint rescaled", 30)

            # Update setPoint status
            self.status.tof_middleSetHV    = self.HVPS.Middle.setVoltage
            self.status.tof_retarderSetHV  = self.HVPS.Retarder.setVoltage
            self.status.tof_meshSetHV      = self.HVPS.Mesh.setVoltage
            self.status.mcp_phosphorSetHV   = self.HVPS.Phosphor.setVoltage
            self.status.mcp_backSetHV       = self.HVPS.Back.setVoltage
            self.status.mcp_frontSetHV      = self.HVPS.Front.setVoltage

            if self.HVPS.tofEnable and self.HVPS.mcpEnable:
                self.status.HV_Status = "OK"
            elif not self.HVPS.tofEnable and not self.HVPS.mcpEnable:
                self.status.HV_Status = "OFF"
            else:
                self.status.HV_Status = "WARNING"

        # IF update failed, HVPS is probably off/disconnected.
        # Set everything to NaN
        except Exception:
            self.status.mcp_hvEnable = False
            self.status.tof_hvEnable = False
            self.status.mcp_phosphorHV  = math.nan
            self.status.mcp_backHV      = math.nan
            self.status.mcp_frontHV     = math.nan
            self.status.tof_middleHV    = math.nan
            self.status.tof_retarderHV  = math.nan
            self.status.tof_meshHV      = math.nan
            self.status.mcp_phosphorSetHV   = math.nan
            self.status.mcp_backSetHV       = math.nan
            self.status.mcp_frontSetHV      = math.nan
            self.status.tof_middleSetHV     = math.nan
            self.status.tof_retarderSetHV   = math.nan
            self.status.tof_meshSetHV       = math.nan
            self.status.HV_Status = "ERROR"
            self.setMessage("ERROR: Cannot connect to HVPS, check NIM crate", 5)
            print(traceback.format_exc())
            self.HVPS.close()

        if self.controls_stop.is_set():
            try:
                self.HVPS.tofEnable = False
                self.HVPS.mcpEnable = False
                self.status.tof_hvEnable = False
                self.status.mcp_hvEnable = False
            except Exception:
                pass
            self.HVPS.close()
        else:
            threading.Timer(config.HVPS.UpdatePeriod, self.HVPSController).start()

def main():
    expManager = UrsapqManager()

    while True:
        try:
            expManager.start()
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
