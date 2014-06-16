#!/usr/bin/python

import sys
import io

class PrintFile:
    file = None
    fileName = None

    OP_FIRING = 1
    OP_MOVE = ord('M')
    CMD_TERMINATOR = '\n'

    opCodes = {}

    def __init__(self, fileName):
        self.registerOpCode(self.OP_FIRING, 'OP_FIRING', name='Firing', format='\x01 ...', handler=self.readFiringCommand)
        self.registerOpCode(self.OP_MOVE, 'OP_MOVE', name='Incremental Movement', format='M <axis> <steps>', handler=self.readMovementCommand)

        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

    def registerOpCode(self, code, codeString, name=None, format=None, handler=None):
        description = {
            'code': codeString,
            'name': name,
            'format': format,
            'handler': handler
        }

        self.opCodes[code] = description

    def peekByte(self):
        byte = self.file.peek(1)

        if byte:
            return byte[0]
        else:
            return None

    def nameForOpCode(self, opcode):
        return self.opCodes[opcode]['name']

    def handlerForOpCode(self, opcode):
        return self.opCodes[opcode]['handler']

    def readFiringCommand(self):
        packet = self.file.read(8) # Burn 7 bytes for now

        print('{},{} - {},{}'.format(ord(packet[1]), ord(packet[2]), ord(packet[5]), ord(packet[6])))

        return packet

    def readMovementCommand(self):
        packet = self.file.readline()

        return packet

    def nextCommand(self):
        byte = self.peekByte()

        if byte:
            opCode = ord(byte)
        else:
            return None

        while True:
            if opCode in self.opCodes:
                print(self.opCodes[opCode]['name'])

                handler = self.handlerForOpCode(opCode)

                if handler:
                    return handler()
                else:
                    return None
            else:
                print('Unknown Code: {}'.format(byte))


class PrintFileParser:
    printFile = None

    positions = {'X': 0, 'Y': 0}
    maximums  = {'X': 0, 'Y': 0}

    def __init__(self, fileName):
        if fileName:
            self.printFile = PrintFile(fileName)

    def parse(self):

        byte = self.printFile.peekByte()

        while byte:
            #print byte
            byte = ord(byte)

            if byte == PrintFile.OP_FIRING:
                #print('Got firing command.')

                packet = self.printFile.file.read(8) # Burn 7 bytes for now

                #print('{},{} - {},{}'.format(ord(packet[1]), ord(packet[2]), ord(packet[5]), ord(packet[6])))

            if byte == PrintFile.OP_MOVE:
                #print('Got movement command.')

                packet = self.printFile.file.readline()

                # Format:
                # M [X, Y] <increment>\n
                # Strategy: split on spaces, check second variable, and int() third.
                packet = packet.split()

                axis = str(packet[1])
                increment = int(packet[2])

                increment = abs(increment)

                if increment > 0:
                    self.positions[axis] += increment
                elif increment == 0:
                    #print('Homing {} axis.'.format(axis))
                    self.positions[axis] = 0
                #else:
                #    print('Negative movement: {} on {} [{}].'.format(increment, axis, positions[axis]))

                for axis in self.positions:
                    if self.positions[axis] > self.maximums[axis]:
                        self.maximums[axis] = self.positions[axis]

                #print(packet[:-1])

            byte = self.printFile.peekByte()
            #a = input('')


if __name__ == '__main__':
    print('Argentum File Parser')

    if len(sys.argv) < 2:
        print('usage: {} <filename>'.format(sys.argv[0]))
        sys.exit(-1)

    inputFileName = sys.argv[1]
    #inputFile = io.open(inputFileName, mode='rb')

    pf = PrintFile(inputFileName)

    while pf.nextCommand():
        pass
    #pf.nextCommand()

    parser = PrintFileParser(inputFileName)
    parser.parse()

    #print('Positions: {}'.format(parser.positions))
    #print('Maximums: {}'.format(parser.maximums))
