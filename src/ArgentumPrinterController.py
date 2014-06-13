from PrinterController import PrinterController

from serial import Serial

class ArgentumPrinterController(PrinterController):
    serialDevice = None
    portName = None
    connected = False

    def __init__(self, portName=None):
        self.portName = portName

    def connect(self, portName=None):
        if portName:
            self.portName = portName

        #print('Attempting to open communication on port {}'.format(self.portName))

        try:
            self.serialDevice = Serial(self.portName)
            self.connected = True

            return True
        except:
            #print('Error opening port {}'.format(self.portName))

            return False

    def disconnect(self):
      self.serialDevice.close()
      self.serialDevice = None
      self.connected = False

    def command(self, command):
        print('[APC] Raw Command Issued: [{}]'.format(command))

        if self.serialDevice and self.connected:
            self.serialDevice.write(command)

    def move(self, x, y):
        if(x):
            self.command('M X {}'.format(x))

        if(y):
            self.command('M Y {}'.format(y))

    def fire(self, address, primitive):
        print('[APC] Firing Command - {} - {}'.format(address, primitive))

        self.command('\x01{}{}\x00'.format(address, primitive))

    def pause(self):
        self.command('P')

    def resume(self):
        self.command('R')

    def start(self):
        self.command('p')

    def stop(self):
        self.command('S')
