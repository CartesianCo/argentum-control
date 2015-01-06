from PrinterController import PrinterController
from serial import Serial, SerialException
import hashlib
import os
import time
from imageproc import calcDJB2

order = ['8', '4', 'C', '2', 'A', '6', 'E', '1', '9', '5', 'D', '3', 'B'];
MAX_FIRING_LINE_LEN = 13*4+12

class ArgentumPrinterController(PrinterController):
    serialDevice = None
    port = None
    connected = False
    delimiter = '\n'
    lastError = None
    version = None

    def __init__(self, port=None):
        self.port = port

    def clearVersion(self):
        self.version = None
        self.majorVersion = None
        self.minorVersion = None
        self.patchVersion = None
        self.buildVersion = None
        self.tagVersion   = None

    def serialWrite(self, strval):
        self.serialDevice.write(strval.encode('utf-8'))

    def connect(self, port=None):
        if port:
            self.port = port

        try:
            self.serialDevice = Serial(self.port, 115200, timeout=0)
            self.connected = True

            self.clearVersion()
            junkBeforeVersion = []
            while True:
                response = self.waitForResponse(timeout=5, expect='\n')
                if response == None:
                    print("No response from printer")
                    break
                goodVersion = None
                for line in response:
                    if line.find('+') <= 0:
                        if line != '':
                            print("Adding junk before version '{}'".format(line))
                            junkBeforeVersion.append(line)
                    else:
                        print("Found a version: {}".format(line))
                        goodVersion = line
                if goodVersion:
                    response = [goodVersion]
                    break
            self.junkBeforeVersion = junkBeforeVersion
            self.serialWrite("notacmd\n")
            if response == None:
                self.lastError = "Printer didn't respond."
                return True

            # Parse out the version
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
            self.serialWrite(command + self.delimiter)
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

    def Print(self, filename, path=None, progressFunc=None):
        if progressFunc == None:
            self.command('p ' + filename)
            return

        lines = 100
        if path:
            file = open(path, "r")
            contents = file.read()
            file.close()
            lines = 0
            for line in contents.split('\n'):
                if len(line) > 3 and line[0] == 'M' and line[2] == 'X':
                    lines = lines + 1
            if lines == 0:
                print("couldn't get number of lines in {}".format(path))
                return
            print("{} has {} lines.".format(filename, lines))

        try:
            self.serialDevice.timeout = 2*60
            self.command('p ' + filename)

            pos = 0
            Done = False
            while not Done:
                response = self.waitForResponse(timeout=2*60, expect='\n')
                if response == None:
                    break
                for line in response:
                    if line == ".":
                        pos = pos + 1
                        if not progressFunc(pos, lines):
                            Done = True
                            break
                    if line.find("Print complete") != -1:
                        Done = True
                        break
                    if line.find("Stopping") != -1:
                        Done = True
                        break
        finally:
            self.serialDevice.timeout = 0


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
        try:
            if self.connected and self.serialDevice.timeout == 0:
                data = None
                n = self.serialDevice.inWaiting()
                if n > 0:
                    data = self.serialDevice.read(n)

                if data:
                    return data
        except Exception as e:
            print("monitor exception: {}".format(e))
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
                if resp.lower() == ("+" + filename).lower():
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

    def checkDJB2(self, path):
        file = open(path, 'r')
        contents = file.read()
        file.close()

        if contents[0] == '#' and contents[1] == ' ' and contents[10] == '\n':
            djb2 = contents[2:10]
        else:
            hash = calcDJB2(contents)
            djb2 = "{:08x}".format(hash)

        filename = os.path.basename(path)
        print("asking printer for {} with djb2 {}.".format(filename, djb2))

        response = self.command("djb2 {}".format(filename), timeout=30, expect='\n')
        for line in response:
            if len(line) == 8:
                print("printer has " + line)
            if line == djb2:
                return True
        return False

    def send(self, path, progressFunc=None):
        file = open(path, 'r')
        contents = file.read()
        file.close()

        filename = os.path.basename(path)

        start = time.time()

        size = len(contents)
        compressed = self.compress(contents)
        cmd = "recv {} {}"
        if compressed and len(compressed) * 3 < size:
            print("compression rate {} to 1".format(float(size) / len(compressed)))
            size = len(compressed)
            contents = compressed
            cmd = "recv {} b {}"
        response = self.command(cmd.format(size, filename), timeout=10, expect='\n')
        if response == None:
            print("no response to recv")
            return
        if response[0] != "Ready":
            print("Didn't get Ready, got: ")
            print(response)
            return

        print("sending {} bytes.".format(size))

        hash = 5381
        fails = 0
        pos = 0
        while (pos < size):
            nleft = size - pos
            blocksize = nleft if nleft < 1024 else 1024
            block = contents[pos:pos+blocksize]
            encblock = ""
            oldhash = hash
            for c in block:
                encblock = encblock + chr(ord(c) ^ 0x26)
                cval = ord(c)
                if cval >= 128:
                    cval = -(256 - cval)
                hash = hash * 33 + cval
                hash = hash & 0xffffffff
            encblock = encblock + chr( hash        & 0xff)
            encblock = encblock + chr((hash >>  8) & 0xff)
            encblock = encblock + chr((hash >> 16) & 0xff)
            encblock = encblock + chr((hash >> 24) & 0xff)
            self.serialWrite(encblock)

            self.serialDevice.timeout = 10
            cmd = self.serialDevice.read(1)

            if cmd == "B":
                hash = oldhash
                fails = fails + 1
                if fails > 12:
                    print("Too many failures.")
                    self.serialDevice.timeout = 0
                    return
            elif cmd == "G":
                pos = pos + blocksize
                if progressFunc:
                    if not progressFunc(pos, size):
                        self.serialWrite("C")
                        print("canceled!")
                        break
                else:
                    print("block is good at {}/{}".format(pos, size))
            else:
                print("didn't get a command! got '{}'".format(cmd))
                rest = self.serialDevice.read(30)
                print(rest)
                break

        self.serialDevice.timeout = 0
        if progressFunc:
            print("sent.")
        else:
            progressFunc(size, size)

        end = time.time()
        print("Sent in {} seconds.".format(end - start))

    def compress(self, contents):
        compressed = []
        lastFiringLine = None
        lastFiring = None
        lastParts = []
        firings = []
        for line in contents.split('\n'):
            if len(line) == 0:
                continue
            if line[0] == '#':
                compressed.append(line)
                continue

            if line[0] == 'M':
                if len(firings) > 0:

                    if len(firings) != len(order):
                        print("firing order changed!")
                        return None
                    firingLine = None
                    for i in range(len(firings)):
                        if firings[i][0] != order[i]:
                            print("firing order changed!")
                            return None
                        if firingLine:
                            if firingLine == ".":
                                firingLine = "," + firings[i][1:]
                            else:
                                firingLine = firingLine + "," + firings[i][1:]
                        else:
                            firingLine = firings[i][1:]
                            if firingLine == None or firingLine == "":
                                firingLine = "."
                    if lastFiringLine and firingLine == lastFiringLine:
                        compressed.append('d')
                    else:
                        compressed.append(firingLine)
                    lastFiringLine = firingLine
                    if len(firingLine) > MAX_FIRING_LINE_LEN:
                        print("firing line too long.")
                        return None
                    firings = []
                if line[2:3] == 'X':
                    compressed.append(line[2:3] + line[4:])
                else:
                    compressed.append(line[4:])
            elif line[0] == 'F':
                firing = line[2:]
                if lastFiring and firing[1:] == lastFiring[1:]:
                    firing = firing[0:1]
                else:
                    lastFiring = firing
                    part = None
                    if firing[1:] == "0000":
                        firing = firing[0:1] + 'z'
                    elif firing[1:3] == "00":
                        part = firing[3:5]
                        firing = firing[0:1] + 'z'
                    elif firing[3:5] == "00":
                        part = firing[1:3]
                        firing = firing[0:1]
                    if part:
                        if part in lastParts:
                            firing = firing + chr(ord('a') + lastParts.index(part))
                        else:
                            lastParts.append(part)
                            if len(lastParts) > 25:
                                lastParts.pop(0)
                            firing = firing + part
                firings.append(firing)
            else:
                print("what's this? {}".format(line))
                return None

        return '\n'.join(compressed) + "\n"

    def volt(self):
        response = self.command("volt", expect='\n', timeout=1)
        if response:
            for line in response:
                if line.find(':') != -1 and line.find('volts.') != -1:
                    return float(line[line.find(': ') + 2:line.find(' volts')])
        return 0
