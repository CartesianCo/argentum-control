#!/usr/bin/env python

import sys
import io
from simcon import SimulatorController
from controllers import TestParsingController

class PrintFile:
    file = None
    fileName = None
    fileSize = 0

    opCodes = {}

    def __init__(self, fileName, commandHandler=None):
        self.fileName = fileName

        if commandHandler:
            self.installCommandHandler(commandHandler)

        self.file = io.open(self.fileName, mode='rb')

        self.fileSize = self.file.seek(0, io.SEEK_END)
        self.rewind()

    def installCommandHandler(self, commandHandler):
        self.commandHandler = commandHandler

        commands = self.commandHandler.supportedCommands()

        for command in commands:
            opcode = command['opcode']
            handler = command['handler']

            self.registerOpCode(opcode, handler=handler)

    def rewind(self):
        self.file.seek(0, io.SEEK_SET)

    def registerOpCode(self, code, handler=None):
        description = {
            'handler': handler
        }

        self.opCodes[code] = description

    def handlerForOpCode(self, opcode):
        return self.opCodes[opcode]['handler']

    def peekByte(self):
        byte = self.file.peek(1)

        if byte:
            return byte[0]
        else:
            return None

    def primitivesFromBitMask(self, bitmask):
        primitives = []

        # Hardcoded 8 primitives here
        for i in xrange(8):
            if bitmask & (1 << i):
                primitives.append(i)

        return primitives

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        packet = self.nextCommand()

        if packet:
            return packet
        else:
            raise StopIteration

    def nextCommand(self):
        byte = self.peekByte()

        if byte is not None:
            opCode = ord(byte)
        else:
            return None

        if opCode in self.opCodes:
            self.handlerForOpCode(opCode)(self.file)
            return True
        else:
            print('Unknown Code: {}'.format(byte))
            return None

if __name__ == '__main__':
    print('Argentum File Parser')

    if len(sys.argv) < 2:
        print('usage: {} <filename>'.format(sys.argv[0]))
        sys.exit(-1)

    inputFileName = sys.argv[1]

    th = SimulatorController()
    printFile = PrintFile(inputFileName, commandHandler=th)

    for command in printFile:
        pass

    #parser = PrintFileParser(inputFileName)
    #print(parser.packetCount())
    #parser.parse()

    #print('Positions: {}'.format(parser.positions))
    #print('Maximums: {}'.format(parser.maximums))
