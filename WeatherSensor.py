#!/usr/bin/python3

import time, struct, sys
import serial.tools.list_ports

for i in serial.tools.list_ports.comports():
    COM_port = str(i).split(" ")[0]

class UMBError(BaseException):
    pass

class WS_UMB:

    #def __init__(self, device='/dev/ttyUSB0', baudrate=19200): #Linux
    def __init__(self, device=None, baudrate=19200): #Windows
        self.device = COM_port
        self.baudrate = baudrate
    
    def __enter__(self): 
        import serial
        self.serial = serial.Serial(self.device, baudrate = self.baudrate, parity = serial.PARITY_NONE, 
                stopbits = serial.STOPBITS_ONE, bytesize = serial.EIGHTBITS, interCharTimeout=1)
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.serial.close()
    
    def readFromSerial(self, timeout=1):
        timeout_count = 0
        data = b''
        while True:
            if self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                data = data + new_data
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 10 * timeout:
                    break
                time.sleep(0.01)
        return data
    
    def calc_next_crc_byte(self, crc_buff, nextbyte):
        for i in range (8):
            if( (crc_buff & 0x0001) ^ (nextbyte & 0x01) ):
                x16 = 0x8408;
            else:
                x16 = 0x0000;
            crc_buff = crc_buff >> 1;
            crc_buff ^= x16;
            nextbyte = nextbyte >> 1;
        return(crc_buff);
    
    def calc_crc16(self, data):
        crc = 0xFFFF;
        for byte in data:
            crc = self.calc_next_crc_byte(crc, byte);
        return crc
    
    def send_request(self, receiver_id, command, command_version, payload):
        
        SOH, STX, ETX, EOT= b'\x01', b'\x02', b'\x03', b'\x04'
        VERSION = b'\x10'
        TO = int(receiver_id).to_bytes(1,'little')
        TO_CLASS = b'\x70'
        FROM = int(1).to_bytes(1,'little')
        FROM_CLASS = b'\xF0'
        
        LEN = 2
        for payload_byte in payload:
            LEN += 1
        LEN = int(LEN).to_bytes(1,'little')
        
        COMMAND = int(command).to_bytes(1,'little')
        COMMAND_VERSION = int(command_version).to_bytes(1,'little')
        
        # Assemble transmit-frame
        tx_frame = SOH + VERSION + TO + TO_CLASS + FROM + FROM_CLASS + LEN + STX + COMMAND + COMMAND_VERSION + payload + ETX 
        # calculate checksum for trasmit-frame and concatenate
        tx_frame += self.calc_crc16(tx_frame).to_bytes(2, 'little') + EOT
        
        # Write transmit-frame to serial
        self.serial.write(tx_frame) 
        #print([hex(c) for c in tx_frame])
        
        ### < --- --- > ###
        
        # Read frame from serial
        rx_frame = self.readFromSerial()
        #print([hex(c) for c in rx_frame])
        
        # compare checksum field to calculated checksum
        cs_calculated = self.calc_crc16(rx_frame[:-3]).to_bytes(2, 'little')
        cs_received = rx_frame[-3:-1]
        if (cs_calculated != cs_received):
            raise UMBError("RX-Error! Checksum test failed. Calculated Checksum: " + str(cs_calculated) + "| Received Checksum: " + str(cs_received))
        
        # Check the length of the frame
        length = int.from_bytes(rx_frame[6:7], byteorder='little')
        if (rx_frame[8+length:9+length] != ETX):
            raise UMBError("RX-Error! Length of Payload is not valid. length-field says: " + str(length))
        
        # Check if all frame field are valid
        if (rx_frame[0:1] != SOH):
            raise UMBError("RX-Error! No Start-of-frame Character")
        if (rx_frame[1:2] != VERSION):
            raise UMBError("RX-Error! Wrong Version Number")
        if (rx_frame[2:4] != (FROM + FROM_CLASS)):
            raise UMBError("RX-Error! Wrong Destination ID")
        if (rx_frame[4:6] != (TO + TO_CLASS)):
            raise UMBError("RX-Error! Wrong Source ID")
        if (rx_frame[7:8] != STX):
            raise UMBError("RX-Error! Missing STX field")
        if (rx_frame[8:9] != COMMAND):
            raise UMBError("RX-Error! Wrong Command Number")
        if (rx_frame[9:10] != COMMAND_VERSION):
            raise UMBError("RX-Error! Wrong Command Version Number")
            
        status = int.from_bytes(rx_frame[10:11], byteorder='little')
        type_of_value = int.from_bytes(rx_frame[13:14], byteorder='little')     
        value = 0
        
        if type_of_value == 16:     # UNSIGNED_CHAR
            value = struct.unpack('<B', rx_frame[14:15])[0]
        elif type_of_value == 17:   # SIGNED_CHAR
            value = struct.unpack('<b', rx_frame[14:15])[0]
        elif type_of_value == 18:   # UNSIGNED_SHORT
            value = struct.unpack('<H', rx_frame[14:16])[0]
        elif type_of_value == 19:   # SIGNED_SHORT
            value = struct.unpack('<h', rx_frame[14:16])[0]
        elif type_of_value == 20:   # UNSIGNED_LONG
            value = struct.unpack('<L', rx_frame[14:18])[0]
        elif type_of_value == 21:   # SIGNED_LONG
            value = struct.unpack('<l', rx_frame[14:18])[0]
        elif type_of_value == 22:   # FLOAT
            value = struct.unpack('<f', rx_frame[14:18])[0]
        elif type_of_value == 23:   # DOUBLE
            value = struct.unpack('<d', rx_frame[14:22])[0]
        
        return (value, status)
        
    
    def onlineDataQuery (self, channel, receiver_id=1):
        return self.send_request(receiver_id, 35, 16, int(channel).to_bytes(2,'little'))


#temp[degC], rel. humidity[%], rel. air pressure[hpa], wind speed[m/s], wind direction[deg]
#MinMax = ['120', '140', '220', '240', '325', '345', '420', '440', '520', '540']
Channels = ['100', '200', '305', '400', '500']


def getdata():
    weatherData = []
    with WS_UMB() as umb:
        for channel in Channels:
        #for channel in MinMax:
            if 100 <= int(channel) <= 29999:
                value, status = umb.onlineDataQuery(channel)
                if status == 0:
                    weatherData.append(value)
                else:
                    sys.stderr.write("On channel " + str(channel) + " got bad value" + "\n")
    return weatherData          

#print(getdata())

import csv
import datetime

#file = 'Sensordata_' + str(datetime.datetime.now().time()) + '.csv'
file = 'DataOutput.csv' ## Windows Python3

if __name__ == "__main__":
    with open(file, 'w') as f:
        writer = csv.writer(f)
        try:
            while True:
                writer.writerow(getdata())
                print(getdata())
                time.sleep(5) ##Save data every 5 seconds
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
        except:
            print("Other exception")
        finally:
            f.close()


















