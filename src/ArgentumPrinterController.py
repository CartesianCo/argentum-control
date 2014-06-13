from PrinterController import PrinterController
from serial import Serial

class ArgentumPrinterController(PrinterController):
    serialDevice = None
    port = None
    connected = False

    def __init__(self, port=None):
        self.port = port

    def connect(self, port=None):
        if port:
            self.port = port

        try:
            self.serialDevice = Serial(self.port)
            self.connected = True

            return True
        except:
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
        if x is not None:
            self.command('M X {}'.format(x))

        if y is not None:
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
