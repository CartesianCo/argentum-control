from PrinterController import PrinterController
from serial import Serial, SerialException

class ArgentumPrinterController(PrinterController):
    serialDevice = None
    port = None
    connected = False
    delimiter = '\n'
    lastError = None

    def __init__(self, port=None):
        self.port = port

    def connect(self, port=None):
        if port:
            self.port = port

        try:
            self.serialDevice = Serial(self.port, 115200)
            self.connected = True

            return True
	except SerialException as e:
	    self.lastError = str(e)
        except:
	    self.lastError = "Unknown Error"
            return False

    def disconnect(self):
      self.serialDevice.close()
      self.serialDevice = None
      self.connected = False

    def command(self, command):
        if self.serialDevice and self.connected:
            self.serialDevice.write(command)
            self.serialDevice.write(self.delimiter)

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
