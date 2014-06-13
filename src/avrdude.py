#!/usr/bin/python

import subprocess

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

  def flashFile(self, firmwareFileName):
    commandString = self.assembleCommand(firmwareFileName)

    subprocess.Popen(commandString.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  def assembleCommand(self, firmwareFileName):
    commandString = './avrdude -C avrdude.conf -v -c {} -p {} -P {} -b {} -D -U flash:w:{}:i'.format(
    self.protocol, self.boardType, self.port, self.baud, firmwareFileName
    )

    return commandString

"""
print('avrdude executing')
port = self.portName
baud = '57600'
firmwareFileName = inputFileName #'blink.hex'
boardType = 'atmega328p'
protocol = 'arduino'

commandString = './avrdude -C avrdude.conf -v -p {} -c {} -P {} -b {} -D -U flash:w:{}:i'.format(
    boardType, protocol, port, baud, firmwareFileName)

self.appendOutput(commandString)

self.serial.close()

flashSubProcess = subprocess.Popen(commandString.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
self.initialiseComms(self.portName)

output = flashSubProcess.communicate()

self.appendOutput(output[0])
self.appendOutput(output[1])
"""
