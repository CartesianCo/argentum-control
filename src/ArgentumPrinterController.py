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
            self.serialDevice = Serial(self.port, 115200, timeout=0)
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
            self.serialDevice.write(command.encode('utf-8'))
            self.serialDevice.write(self.delimiter.encode('utf-8'))
            return True
        return False

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

    def monitor(self):
        if self.connected and self.serialDevice.inWaiting():
            data = self.serialDevice.read(1)
            n = self.serialDevice.inWaiting()
            if n:
                data = data + self.serialDevice.read(n)

            if data:
                return data
        return None

    def waitForResponse(self):
        if not self.connected:
            return None

        self.serialDevice.timeout = 0.5
        response = ""
        try:
            while True:
                data = self.serialDevice.read(1)
                n = self.serialDevice.inWaiting()
                if n:
                    data = data + self.serialDevice.read(n)
                else:
                    break
                if data:
                    response = response + data
        finally:
            self.serialDevice.timeout = 0

        if response == "":
            return None
        return response

    def missingFiles(self, files):
        self.command("ls")
        response = self.waitForResponse()
        resp_list = response.split("\n")
        missing = []
        for filename in files:
            sdFilename = filename.upper()
            found = False
            for resp in resp_list:
                if resp == "+" + sdFilename:
                    found = True
                    break
            if not found:
                missing.append(filename)
        return missing
