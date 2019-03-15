import time
import serial

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
)

ser.isOpen()

print('Enter your commands below.\r\nInsert "exit" to leave the application.')

cmd=1
while 1 :
    # get keyboard input
    cmd = input(">> ")
        # Python 3 users
        # input = input(">> ")
    if cmd == 'exit':
        ser.close()
        exit()
    else:
        # send the character to the device
        # (note that I happend a \r\n carriage return and line feed to the characters - this is requested by my device)
        ser.write(cmd.encode() + b'\r\n')
        out = b''
        # let's wait one second before reading output (let's give device time to answer)
        time.sleep(2)
        while ser.inWaiting() > 0:
            out += ser.read(1)

        if out != '':
            print("<< " + out.decode())
