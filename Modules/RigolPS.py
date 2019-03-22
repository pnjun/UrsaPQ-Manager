#!python3

#This class is used to manage the Coil power supply connected through serial interface

#Fabiano Lever (fabiano.lever@uni-potsdam.de)

import time
import serial
from serial.tools import list_ports
from config import config

class RigolPS:
    #initialize serial connection and check that serial is isOpen

    def __init__(self, name=config.RigolPS.PS_DeviceName):
        #init serial connection
        self.serial = serial.Serial()
        self.name = name
        self.serial.baudrate = 115200
        self.serial.timeout = 0.2

    def connect(self):
        #Scan all serials looking for matching device name
        self.serial.port = list(list_ports.grep(self.name))[0][0]
        if not self.serial.is_open:
            self.serial.open()

        self.serial.flush()

    #returns a channel
    def __getattr__(self, channelname):

        chid = getattr(config.RigolPS.Channels, channelname)
        serial = self.serial

        class OvenPSChannel:
            #uses the SCPI commands to talk to power supply, read manual in /Manuals folder for explanation
            def on(self):
                serial.write( b':OUTP CH%d, ON\r\n' % int(chid)); serial.flush()

            def off(self):
                serial.write( b':OUTP CH%d, OFF\r\n' % int(chid)); serial.flush()


            def isOn(self):
                serial.write( b':OUTP? CH%d\r\n' % int(chid)); serial.flush()
                time.sleep(0.01)
                str = serial.readline()
                if str == b'OFF\n':
                    return False
                elif str == b'ON\n':
                    return True
                else:
                    raise Exception("RigolPS not responding")

            #sets and retrives the set voltage for channel
            @property
            def setVoltage(self):
                serial.write( b':sour%d:volt?\r\n' % int(chid)); serial.flush()
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
    d = RigolPS()
    d.connect()
    print(d.Coil.isOn())
    d.Coil.off()
    d.Coil.setCurrent = 2
    print(d.Coil.setCurrent)
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
