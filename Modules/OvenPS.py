#!python3

#This class is used to manage the HV pover supplies connected through serial interface

#Fabiano Lever (fabiano.lever@uni-potsdam.de)

import time
import serial
from serial.tools import list_ports
from config import config

class OvenPS:
    #initialize serial connection and check that serial is isOpen
    #TODO: implement consistency check on device ID to prevent wrong physical power supply from being connected
    def __init__(self, name=config.Oven.PS_DeviceName):
        #init serial connection
        self.serial = serial.Serial()
        self.name = name
        self.serial.baudrate = 9600
        self.serial.timeout = 0.3

    def connect(self):
        #Scan all serials looking for matching device name
        self.serial.port = list(list_ports.grep(self.name))[0][0]
        if not self.serial.is_open:
            self.serial.open()

        self.serial.flush()

    def allOn(self):
        for key, val in config.Oven.Channels._asdict().items():
            self.__getattr__(key).on()

    def allOff(self):
        for key, val in config.Oven.Channels._asdict().items():
            self.__getattr__(key).off()

    #returns a channel
    def __getattr__(self, channelname):

        chid = getattr(config.Oven.Channels, channelname)
        serial = self.serial

        class OvenPSChannel:
            #uses the SCPI commands to talk to power supply, read manual in /Manuals folder for explanation
            def on(self):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':OUTP ON\r\n'); serial.flush()

            def off(self):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':OUTP OFF\r\n'); serial.flush()

            #sets and retrives the set voltage for channel
            @property
            def setVoltage(self):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':VOLT?\r\n'); serial.flush()
                return float (serial.readline())

            @setVoltage.setter
            def setVoltage(self, val):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':VOLT %f' % float(val) + b'\r\n'); serial.flush()

            #retrives actual measured voltage on channel
            @property
            def voltage(self):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':MEAS:VOLT?\r\n'); serial.flush()
                return float(serial.readline())

            #retrives actual measured power output on channel
            @property
            def power(self):
                serial.write( b':INST OUT%d' % int(chid) + b'\r\n'); serial.flush()
                serial.write( b':MEAS:POW?\r\n'); serial.flush()
                return float(serial.readline())

        return OvenPSChannel()

if __name__=='__main__':
    d = OvenPS()
    d.connect()
    d.Body.off()
    d.Body.setVoltage = 2.22
    print(d.Body.setVoltage)
    print(d.Body.voltage)

    d.Body.on()
    time.sleep(2)
    print(d.Body.voltage)

    d.Body.off()
    time.sleep(1)
    print(d.Body.voltage)
