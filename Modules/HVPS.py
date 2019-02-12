#!python3

#This class is used to manage the HV pover supplies connected through serial interface

#Fabiano Lever (fabiano.lever@uni-potsdam.de)

import time
from serial import Serial

class HVPS:
    #initialize serial connection and check that serial is isOpen
    #TODO: implement consistency check on device ID to prevent wrong physical power supply from being connected
    def __init__(self, serialPort):
        #init serial connection
        self.serial = Serial( port=serialPort, baudrate=9600 , timeout=0.1)
        self.serial.isOpen()

    #returns a channel
    def __getitem__(self, chid):

        if not isinstance(chid, int):
            raise TypeError("Channel index must be an int")

        if chid > 5 or chid < 0:
            raise ValueError("Channel index must be between 0 and 5")

        serial = self.serial

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
    print("Running test on channel 5")

    d = HVPS('/dev/ttyUSB0')
    d[5].setVoltage = 20
    print(d[5].setVoltage)
    print(d[5].voltage)

    d[5].on()
    time.sleep(1)
    print(d[5].voltage)

    d[5].off()
    time.sleep(1)
    print(d[5].voltage)
