#!python3

#This class is used to manage the HV pover supplies connected through serial interface

#Fabiano Lever (fabiano.lever@uni-potsdam.de)

import time
import serial
from serial.tools import list_ports
from config import config

class HVPS:
    #initialize serials connection and check that serial is isOpen

    def __init__(self, posName = config.HVPS.Pos_Devicename,
                       negName = config.HVPS.Neg_Devicename):
        #init serial connection
        self.posSerial = serial.Serial()
        self.negSerial = serial.Serial()
        self.posName = posName
        self.negName = negName
        self.posSerial.baudrate = 9600
        self.posSerial.timeout = 0.02
        self.negSerial.baudrate = 9600
        self.negSerial.timeout = 0.02

        self._mcpEnable = False
        self._tofEnable = False

    def connect(self):
        #Scan all serials looking for matching device name
        try:
            self.posSerial.port = list(list_ports.grep(self.posName))[0][0]
            self.negSerial.port = list(list_ports.grep(self.negName))[0][0]
        except IndexError:
            raise Exception("Cannot find HVPS, is it on?")
        
        if not self.posSerial.is_open:
            self.posSerial.open()
        if not self.negSerial.is_open:
            self.negSerial.open()

        self.posSerial.flush()
        self.negSerial.flush()

    def close(self):
        if self.posSerial.is_open:
            self.posSerial.close()
        if self.negSerial.is_open:
            self.negSerial.close()

    @property
    def mcpEnable(self):
        return self._mcpEnable

    @mcpEnable.setter
    def mcpEnable(self, enable):
        for key,val in config.HVPS.MCP_Channels._asdict().items():
            if enable:
                self.__getattr__(key).on()
                self._mcpEnable = True
            else:
                self.__getattr__(key).off()
                self._mcpEnable = False

    @property
    def tofEnable(self):
        return self._tofEnable

    @tofEnable.setter
    def tofEnable(self, enable):
        self.posSerial.write( b'*CLS' + b'\r\n'); self.posSerial.flush() # Reset events
        self.negSerial.write( b'*CLS' + b'\r\n'); self.negSerial.flush() # Reset events

        for key,val in config.HVPS.TOF_Channels._asdict().items():
            if enable:
                self.__getattr__(key).on()
                self._tofEnable = True
            else:
                self.__getattr__(key).off()
                self._tofEnable = False

    #returns a channel
    def __getattr__(self, channelname):

        try:
            channel = getattr(config.HVPS.MCP_Channels, channelname)
        except AttributeError:
            channel = getattr(config.HVPS.TOF_Channels, channelname)

        chid = int( channel[0] ) #first char is channel num
        serial = self.posSerial if channel[1] == 'p' else self.negSerial

        class HVPSChannel:
            #uses the SCPI commands to talk to power supply, read manual in /Manuals folder for explanation
            def on(self):
                serial.write( b':VOLT ON,(@%d)' % int(chid) + b'\r\n'); serial.flush()

            def off(self):
                serial.write( b':VOLT OFF,(@%d)' % int(chid) + b'\r\n'); serial.flush()

            #sets and retrives the set voltage for channel
            @property
            def setVoltage(self):
                serial.write( b':READ:VOLT?(@%d)' % int(chid) + b'\r\n'); serial.flush()
                return float (serial.readlines()[-1][:-3]) #takes last line (first line is just the command), and removes ending characters before converting to float

            @setVoltage.setter
            def setVoltage(self, val):
                serial.write( b':VOLT %f,(@%d)' % (float(val), int(chid)) + b'\r\n'); serial.flush()

            #retrives actual measured voltage on channel
            @property
            def voltage(self):
                serial.write( b':MEAS:VOLT?(@%d)' % int(chid) + b'\r\n'); serial.flush()
                return float (serial.readlines()[-1][:-3])  #takes last line (first line is just the command), and removes ending characters before converting to float

        return HVPSChannel()

if __name__=='__main__':
    print("Running test on MeshCh")

    d = HVPS()
    d.connect()
    d.Mesh.setVoltage = 20
    print(d.Mesh.setVoltage)
    print(d.Mesh.voltage)

    d.Mesh.on()
    time.sleep(4)
    print(d.Mesh.voltage)

    d.Mesh.off()
    time.sleep(1)
    print(d.Mesh.voltage)
