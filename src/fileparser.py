#!/usr/bin/python

import sys
import io

class PrintFile:
    file = None
    fileName = None
    fileSize = 0

    OP_FIRING = 1
    OP_MOVE = ord('M')
    CMD_TERMINATOR = '\n'

    opCodes = {}

    def __init__(self, fileName):
        self.registerOpCode(self.OP_FIRING, handler=self.readFiringCommand)
        self.registerOpCode(self.OP_MOVE, handler=self.readMovementCommand)

        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

        self.fileSize = self.file.seek(0, io.SEEK_END)
        self.rewind()

    def rewind(self):
        self.file.seek(0, io.SEEK_SET)

    def registerOpCode(self, code, handler=None):
        description = {
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

    def primitivesFromBitMask(self, bitmask):
        primitives = []

        # Hardcoded 8 primitives here
        for i in xrange(8):
            if bitmask & (1 << i):
                primitives.append(i)

        return primitives

    def readFiringCommand(self):
        # This is actually TWO firing packets, but they always come in pairs
        # currently, since we have two cartridges.
        packet = self.file.read(8)

        primitive1 = ord(packet[1])
        address1 = ord(packet[2])

        primitive2 = ord(packet[5])
        address2 = ord(packet[6])

        primitive1 = self.primitivesFromBitMask(primitive1)
        primitive2 = self.primitivesFromBitMask(primitive2)

        ret = {
            'firing': [
                [primitive1, address1],
                [primitive2, address2]
            ]
        }

        return ret

    def readMovementCommand(self):
        # Read until the next newline (\n).
        packet = self.file.readline()
        packet = packet.split()

        axis = str(packet[1])
        increment = int(packet[2])

        ret = {
            'incrementalMove': {
                axis: increment
            }
        }

        return ret

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
            return self.handlerForOpCode(opCode)()
        else:
            print('Unknown Code: {}'.format(byte))
            return None


class PrintFileParser:
    printFile = None

    positions = {'X': 0, 'Y': 0}
    maximums  = {'X': 0, 'Y': 0}

    def __init__(self, fileName):
        if fileName:
            self.printFile = PrintFile(fileName)

    def parse(self):
        for packet in self.printFile:
            print packet

    def parse2(self):

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

    parser = PrintFileParser(inputFileName)
    parser.parse()

    print('Positions: {}'.format(parser.positions))
    print('Maximums: {}'.format(parser.maximums))
