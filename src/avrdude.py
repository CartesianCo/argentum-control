#!/usr/bin/python

import sys
import os
import subprocess
import stat

class avrdude:
  def __init__(self, port=None, baud=None, boardType=None, protocol=None):
    self.port = port

    if baud:
      self.baud = baud
    else:
      #self.baud = '57600'
      self.baud = '115200'

    if boardType:
      self.boardType = boardType
    else:
      #self.boardType = 'atmega328p'
      self.boardType = 'atmega2560'

    if protocol:
      self.protocol = protocol
    else:
      #self.protocol = 'arduino'
      self.protocol = 'stk500v2'

    self.running = None

  def flashFile(self, firmwareFileName):
    if self.running != None:
        if self.running.poll() == None:
            self.running = None
        else:
            print("Already flashing!")
            return False

    command = self.assembleCommand(firmwareFileName)

    print("Running: " + ' '.join(command))

    try:
        self.running = subprocess.Popen(command) #, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        print(e)
        print("This usually means we can't find avrdude.")
    except:
        print(sys.exc_info()[0])
        return False

    return True

  def done(self):
    if self.running == None:
        return True
    if self.running.poll() == None:
        return False
    self.running = None
    return True

  def assembleCommand(self, firmwareFileName):
    if os.path.isdir('tools'):
        avrdudeString = './tools/avrdude -C avrdude.conf'
    elif os.path.exists('avrdude') and os.path.exists('avrdude.conf'):
        avrdudeString = './avrdude -C avrdude.conf'
        if not os.access('avrdude', os.X_OK):
            os.chmod('avrdude', stat.S_IREAD | stat.S_IEXEC)
    else:
        # use the system's exe and config
        avrdudeString = 'avrdude'

    command = (avrdudeString + ' -v -c {} -p {} -P {} -b {} -D -U').format(
              self.protocol,
              self.boardType,
              self.port,
              self.baud).split()
    command.append('flash:w:{}:i'.format(firmwareFileName))
    return command
