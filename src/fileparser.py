#!/usr/bin/python

import sys
import io

OP_FIRING = 1
OP_MOVE = ord('M')
CMD_TERMINATOR = '\n'

class PrintFile:
    file = None
    fileName = None

    positions = {'X': 0, 'Y': 0}
    maximums  = {'X': 0, 'Y': 0}

    def __init__(self, fileName):
        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

    def peekByte(self):
        byte = self.file.peek(1)

        if byte:
            return byte[0]
        else:
            return None

    def nextByte(self):
        return self.file.read(1)

    def parse(self):

        byte = self.peekByte()

        while byte:
            #print byte
            byte = ord(byte)

            if byte == OP_FIRING:
                #print('Got firing command.')

                packet = self.file.read(8) # Burn 7 bytes for now

                #print('{},{} - {},{}'.format(ord(packet[1]), ord(packet[2]), ord(packet[5]), ord(packet[6])))

            if byte == OP_MOVE:
                #print('Got movement command.')

                packet = self.file.readline()

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

            byte = self.peekByte()
            #a = input('')


if __name__ == '__main__':
    print('Argentum File Parser')

    if len(sys.argv) < 2:
        print('usage: {} <filename>'.format(sys.argv[0]))
        sys.exit(-1)

    inputFileName = sys.argv[1]
    #inputFile = io.open(inputFileName, mode='rb')

    parser = PrintFile(inputFileName)
    parser.parse()

    print('Positions: {}'.format(parser.positions))
    print('Maximums: {}'.format(parser.maximums))
