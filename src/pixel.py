#!/usr/bin/env python

import sys
from printfile import PrintFile

from PIL import Image

positions = {'X': 0, 'Y': 0}
maximums  = {'X': 0, 'Y': 0}

def maximum_size(file):
    for command in file:
        if command[0] == 'move':
            data = command[1][0]
            data = data.items()[0]

            axis = data[0]
            steps = int(data[1])

            if steps == 0:
                positions[axis] = 0
            else:
                positions[axis] += abs(steps)

            for key in positions:
                if positions[key] > maximums[key]:
                    maximums[key] = positions[key]

    file.rewind()

    return maximums


if __name__ == '__main__':
    print('Argentum File Parser')

    if len(sys.argv) < 2:
        print('usage: {} <filename>'.format(sys.argv[0]))
        sys.exit(-1)

    inputFileName = sys.argv[1]

    printFile = PrintFile(inputFileName)

    #for command in printFile:
    #    print command

    size = maximum_size(printFile)

    print size

    width = size['X'] + 104
    height = size['Y'] + 104

    out = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    matrix = out.load()

    for command in printFile:
        if command[0] == 'move':
            data = command[1][0]
            data = data.items()[0]

            axis = data[0]
            steps = int(data[1])

            if steps == 0:
                positions[axis] = 0
            else:
                positions[axis] += abs(steps)

        if command[0] == 'firing':
            data = command[1]

            cartridge1 = data[0]
            cartridge2 = data[1]

            firing1 = cartridge1[0]
            address1 = cartridge1[1]

            firing2 = cartridge2[0]
            address2 = cartridge2[1]

            print (firing1, address1)
            print 'firing'
            print positions
            matrix[positions['X'], positions['Y']] = 255

    out.save('out.jpg')

def offset_for_nozzle(nozzle):
    return (0, 0)

def nozzle_from_primitive_and_address(primitive, address):
    return 0

def primitives_from_bitmask(bitmask):
    primitives = []

    # Hardcoded 8 primitives here
    for i in xrange(8):
        if bitmask & (1 << i):
            primitives.append(i)

    return primitives

# The primitive defines the column the nozzle is in, and an overall Y position
# The address is merely and offset from that Y position (and a slight X, to be
# handled in the future.)

# Primitives start at 0 and ODD

def column_from_primitive(primitive):
    return primitive % 2

    #parser = PrintFileParser(inputFileName)
    #print(parser.packetCount())
    #parser.parse()

    #print('Positions: {}'.format(parser.positions))
    #print('Maximums: {}'.format(parser.maximums))
