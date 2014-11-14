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

    def command(self, command, timeout=0, expect=None):
        if self.serialDevice and self.connected:
            self.serialDevice.timeout = timeout
            self.serialDevice.write(command.encode('utf-8'))
            self.serialDevice.write(self.delimiter.encode('utf-8'))
            if timeout != 0:
                return self.waitForResponse(timeout, expect)
            return True
        return None

    def move(self, x, y):
        if x is not None:
            self.command('M X {}'.format(x))

        if y is not None:
            self.command('M Y {}'.format(y))

    def home(self, wait=False):
        if wait:
            self.command('home', 30, '+Homed')
        else:
            self.command('home')

    def calibrate(self):
        self.command('c')

    def isHomed(self):
        response = self.command('lim', 1)
        for resp in response:
            if resp == "+Limits: X- Y- ":
                return True
        return False

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
        if (self.connected and
                self.serialDevice.timeout == 0 and
                self.serialDevice.inWaiting()):
            data = None
            n = self.serialDevice.inWaiting()
            if n > 0:
                #print("monitor reading {} bytes.".format(n))
                data = self.serialDevice.read(n)

            if data:
                #print("monitor returned data.")
                return data
        return None

    def waitForResponse(self, timeout=0.5, expect=None):
        if not self.connected:
            return None

        self.serialDevice.timeout = timeout
        response = ""
        try:
            while True:
                data = self.serialDevice.read(1)
                n = self.serialDevice.inWaiting()
                if n > 0:
                    #print("waitForResponse reading {} more bytes.".format(n))
                    data = data + self.serialDevice.read(n)
                else:
                    break
                if data:
                    response = response + data

                if expect:
                    if response.find(expect) != -1:
                        break
        finally:
            self.serialDevice.timeout = 0

        if response == "":
            return None

        response = response.split('\n')
        resp_list = []
        for resp in response:
            if resp.find('\r') != -1:
                resp = resp[:resp.find('\r')]
            resp_list.append(resp)
        return resp_list

    def missingFiles(self, files):
        response = self.command("ls", 2)
        missing = []
        for filename in files:
            found = False
            for resp in response:
                if resp == ("+" + filename):
                    found = True
                    break
            if not found:
                missing.append(filename)
        return missing
