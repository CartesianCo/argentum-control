from PrinterController import PrinterController
from serial import Serial, SerialException
import hashlib
import os

class ArgentumPrinterController(PrinterController):
    serialDevice = None
    port = None
    connected = False
    delimiter = '\n'
    lastError = None
    version = None

    def __init__(self, port=None):
        self.port = port

    def connect(self, port=None):
        if port:
            self.port = port

        try:
            self.serialDevice = Serial(self.port, 115200, timeout=0)
            self.connected = True

            response = self.waitForResponse(timeout=2, expect='\n')
            if response == None:
                self.lastError = "Printer didn't respond."
                self.connected = False
                return False

            # Parse out the version
            self.version = None
            for line in response:
                if line.find('.') == -1:
                    continue
                major = line[:line.find('.')]
                line = line[line.find('.')+1:]
                if line.find('.') == -1:
                    continue
                minor = line[:line.find('.')]
                line = line[line.find('.')+1:]
                if line.find('+') == -1:
                    continue
                patch = line[:line.find('+')]
                build = line[line.find('+')+1:].rstrip()
                if len(build) != 8:
                    continue

                tag = None
                if patch.find('-') != -1:
                    tag = patch[patch.find('-')+1:]
                    patch = patch[:patch.find('-')]

                try:
                    major = int(major)
                    minor = int(minor)
                    patch = int(patch)
                except ValueError:
                    continue

                self.version = "{}.{}.{}".format(major, minor, patch)
                if tag:
                    self.version = self.version + "-" + tag
                self.version = self.version + "+" + build

                self.majorVersion = major
                self.minorVersion = minor
                self.patchVersion = patch
                self.buildVersion = build
                self.tagVersion   = tag

                print("Printer is running version: " + self.version)
                break

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
      self.version = None

    def command(self, command, timeout=None, expect=None, wait=False):
        if self.serialDevice and self.connected:
            if timeout:
                self.timeout = timeout
            self.serialDevice.write(command.encode('utf-8'))
            self.serialDevice.write(self.delimiter.encode('utf-8'))
            if wait != False:
                if timeout == None:
                    timeout = 30
                if expect == None:
                    expect = command
            if timeout:
                return self.waitForResponse(timeout, expect)
            return True
        return None

    def move(self, x, y, wait=False):
        if x is not None:
            self.command('M X {}'.format(x), wait=wait)

        if y is not None:
            self.command('M Y {}'.format(y), wait=wait)

    def home(self, wait=False):
        if wait:
            self.command('home', timeout=30, expect='+Homed')
        else:
            self.command('home')

    def calibrate(self):
        self.command('c')

    def Print(self, filename, wait=False):
        if wait:
            self.command('p ' + filename, timeout=2*60, expect="+Print complete")
        else:
            self.command('p ' + filename)

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
                    response = response + data.decode('utf-8', 'ignore')

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
        response = self.command("ls", timeout=2)
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

    def checkMd5(self, filename):
        file = open(filename, 'r')
        contents = file.read()
        file.close()
        m = hashlib.md5()
        m.update(contents)
        md5 = m.hexdigest()
        response = self.command("md5 {}".format(os.path.basename(filename)), timeout=10, expect='\n')
        for line in response:
            if line == md5:
                return True
        return False

    def checkDJB2(self, filename):
        file = open(filename, 'r')
        contents = file.read()
        file.close()

        hash = 5381
        for c in contents:
            cval = ord(c)
            if cval >= 128:
                cval = -(256 - cval)
            hash = hash * 33 + cval
            hash = hash & 0xffffffff
        djb2 = "{:08x}".format(hash)

        response = self.command("djb2 {}".format(os.path.basename(filename)), timeout=10, expect='\n')
        print("looking for:", djb2)
        for line in response:
            print("got:", line)
            if line == djb2:
                return True
        return False

