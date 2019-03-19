#!python3

#This class is used to manage the Coil power supply connected through serial interface

#Fabiano Lever (fabiano.lever@uni-potsdam.de)

import time
import serial
from serial.tools import list_ports
from config import config

class CoilPS:
    #initialize serial connection and check that serial is isOpen

    def __init__(self, name=config.Coil.PS_DeviceName):
        #init serial connection
        self.serial = serial.Serial()
        self.name = name
        self.serial.baudrate = 115200
        self.serial.timeout = 2

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

        chid = getattr(config.Coil.Channels, channelname)
        serial = self.serial

        class OvenPSChannel:
            #uses the SCPI commands to talk to power supply, read manual in /Manuals folder for explanation
            def on(self):
                serial.write( b':OUTP CH%d, ON\r\n' % int(chid)); serial.flush()

            def off(self):
                serial.write( b':OUTP CH%d, OFF\r\n' % int(chid)); serial.flush()

            #sets and retrives the set voltage for channel
            @property
            def setVoltage(self):
                serial.write( b':sour%d:volt ?\r\n' % int(chid)); serial.flush()
                return float (serial.readline())

            @setVoltage.setter
            def setVoltage(self, val):
                serial.write( b':sour%d:volt %f\r\n' % (int(chid), val)); serial.flush()

            #sets and retrives the set current for channel
            @property
            def setCurrent(self):
                serial.write( b':sour%d:current?\r\n' % int(chid)); serial.flush()
                return float (serial.readline())

            @setCurrent.setter
            def setCurrent(self, val):
                serial.write( b':sour%d:current %f\r\n' % (int(chid), val)); serial.flush()


            #retrives actual measured voltage on channel
            @property
            def voltage(self):
                serial.write( b':meas:volt? ch%d\r\n' % int(chid)); serial.flush()
                return float (serial.readline())

            #retrives actual measured current on channel
            @property
            def current(self):
                serial.write( b':meas:current? ch%d\r\n' % int(chid)); serial.flush()
                return float (serial.readline())

            #retrives actual measured power output on channel
            @property
            def power(self):
                serial.write( b':meas:powe? ch%d\r\n' % int(chid)); serial.flush()
                return float (serial.readline())

        return OvenPSChannel()

if __name__=='__main__':
    d = CoilPS()
    d.connect()
    d.Coil.on()
    d.Coil.setVoltage = 1.43
    print(d.Coil.setVoltage)
    print(d.Coil.voltage)
    print()

    d.Coil.on()
    time.sleep(2)
    print(d.Coil.voltage)
    print(d.Coil.power)
    print()

    d.Coil.off()
    time.sleep(1)
    print(d.Coil.voltage)
