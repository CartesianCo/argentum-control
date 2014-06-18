#!/usr/bin/env python

import sys
import io
from simcon import SimulatorController
from controllers import TestParsingController

class PrintFile:
    file = None
    filename = None
    filesize = 0

    def __init__(self, filename):
        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

        self.fileSize = self.file.seek(0, io.SEEK_END)
        self.rewind()

    def rewind(self):
        self.file.seek(0, io.SEEK_SET)

    def peekByte(self):
        byte = self.file.peek(1)

        if byte:
            return byte[0]
        else:
            return None

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
    print('Argentum File Parser V1')

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
