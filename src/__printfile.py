#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington
    Copyright (C) 2015 Michael Reed

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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
