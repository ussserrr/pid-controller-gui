import socket
from random import random
from time import sleep
from PyQt5.QtCore import QObject, pyqtSignal


class MCUconn():
    OFFLINE_MODE = False

    class Signal(QObject):
        signal = pyqtSignal()


    def __init__(self, IPaddr, UDPport):
        self.IP = IPaddr
        self.PORT = UDPport

        # Create socket. AF_INET corresponds to IPv4 address type
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 1 seconds timeout
        self.sock.settimeout(1.0)

        self.connLost = self.Signal()


    def parser(self, coef):
        """
        Always return tuple of 1 or 2 floats (string in one case) for standardizing
        """
        if not self.OFFLINE_MODE:
            try:
                data, addr = self.sock.recvfrom(128)
            except socket.timeout:
                self.connLost.signal.emit()
                return ( 0.0, 0.0 )
        else:
            sleep(0.025)  # fake delay, else too many values
            return ( random(), random() )

        if coef == 'U':
            return ( float(data)*3.3/4095.0, )
        elif coef=='PerrLimits' or coef=='IerrLimits':
            return ( float(data[:16]), float(data[17:]) )
        elif coef == 'SaveToEEPROM':
            return ( data.decode('utf-8'), )
        else:
            return ( float(data), )


    def read(self, coef):
        if coef == 'U':
            self.write('u')
        elif coef == 'PID':
            self.write('p')
        elif coef == 'setpoint':
            self.write('spRead')
        elif coef == 'Kp':
            self.write('KpRead')
        elif coef == 'Ki':
            self.write('KiRead')
        elif coef == 'Kd':
            self.write('KdRead')
        elif coef == 'Ierr':
            self.write('IerrRead')
        elif coef == 'PerrLimits':
            self.write('PerrLIMr')
        elif coef == 'IerrLimits':
            self.write('IerrLIMr')

        return self.parser(coef)


    def write(self, coef, *values):
        writeString = ''

        # If we want to write some values in MCU
        if coef == 'setpoint':
            writeString = 'spWrite {}'.format(values[0])
        elif coef == 'Kp':
            writeString = 'KpWrite {}'.format(values[0])
        elif coef == 'Ki':
            writeString = 'KiWrite {}'.format(values[0])
        elif coef == 'Kd':
            writeString = 'KdWrite {}'.format(values[0])
        elif coef == 'PerrLimits':
            writeString = 'PerrLIMw {:16.3f} {:16.3f}'.format(values[0], values[1])
        elif coef == 'IerrLimits':
            writeString = 'IerrLIMw {:16.3f} {:16.3f}'.format(values[0], values[1])

        # write command received from another function
        else:
            writeString = coef

        if not self.OFFLINE_MODE:
            self.sock.sendto(writeString.encode('utf-8'), (self.IP, self.PORT))


    def resetIerr(self):
        self.write('IerrRST')


    def saveCurrentValues(self):
        self.setpoint = self.read('setpoint')[0]
        self.Kp = self.read('Kp')[0]
        self.Ki = self.read('Ki')[0]
        self.Kd = self.read('Kd')[0]
        self.PerrLimits = self.read('PerrLimits')
        self.IerrLimits = self.read('IerrLimits')


    def restoreValues(self):
        self.write('setpoint', self.setpoint)
        self.write('Kp', self.Kp)
        self.write('Ki', self.Ki)
        self.write('Kd', self.Kd)
        self.write('PerrLimits', self.PerrLimits[0], self.PerrLimits[1])
        self.write('IerrLimits', self.IerrLimits[0], self.IerrLimits[1])


    def saveToEEPROM(self):
        self.write('SaveToEEPROM')

        if self.parser('SaveToEEPROM')[0]=='success':
            return 0
        else:
            return 1


    def checkConnection(self):
        try:
            self.sock.sendto('u'.encode('utf-8'), (self.IP, self.PORT))
            data, addr = self.sock.recvfrom(128)
        except socket.timeout:
            return 1
        return 0
