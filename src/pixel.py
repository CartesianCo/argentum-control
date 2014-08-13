#!/usr/bin/env python

import sys
from printfile import PrintFile

from PIL import Image
from CartridgeMath import offset_for_nozzle, nozzle_from_primitive_address

SPN = 3.386666
positions = {'X': 104 * SPN, 'Y': 104 * SPN}
maximums  = {'X': 104, 'Y': 104}
maximum_value = 0

def flip(a):
    b = 0

    b = (a & 0b00000001) << 3
    b |= (a & 0b00000010) << 1
    b |= (a & 0b00000100) >> 1
    b |= (a & 0b00001000) >> 3

    return b

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

def maximum_size(file):
    for command in file:
        if command[0] == 'move':
            data = command[1][0]
            data = data.items()[0]

            axis = data[0]
            steps = int(data[1]) / SPN

            if steps == 0:
                positions[axis] = 0
            else:
                positions[axis] += abs(steps)

            for key in positions:
                if positions[key] > maximums[key]:
                    maximums[key] = positions[key]

    file.rewind()

    return maximums

def fire_with_offset(offset):
    global maximum_value
    x_offset, y_offset = offset

    firing_offset = (x_offset + int(round(positions['X'])), y_offset + int(round(positions['Y'])))

    #print firing_offset

    try:
        matrix[firing_offset] = (0, 0, 0, 255)

        if matrix[firing_offset][0] > maximum_value:
            maximum_value = matrix[firing_offset][0]

    except IndexError:
        print("{} cause index error.".format(firing_offset))
        print("Given: {}".format(offset))
        print("Current position: {}".format((positions['X'], positions['Y'])))
        while(1):
            pass

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

    width = int(round(size['X'] + 104 * SPN))
    height = int(round(size['Y'] + 104 * SPN))

    positions['X'] = 0
    positions['Y'] = 0

    out = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    matrix = out.load()

    for command in printFile:
        if command[0] == 'move':
            data = command[1][0]
            data = data.items()[0]

            #print command

            axis = data[0]
            steps = int(data[1])

            if axis == 'Y':
                steps = -steps
                print command

            if steps == 0:
                positions[axis] = 0
            else:
                positions[axis] += steps / SPN

        if command[0] == 'firing':
            data = command[1]

            cartridge1 = data[0]
            cartridge2 = data[1]

            firing1 = cartridge1[0]
            address1 = cartridge1[1]

            firing2 = cartridge2[0]
            address2 = cartridge2[1]

            address1 = flip(address1) - 1
            address2 = flip(address2) - 1

            """
            print (firing1, bin(address1))
            print 'firing'
            print positions
            """

            primitives = primitives_from_bitmask(firing1)

            #print primitives

            for primitive in primitives:
                #print primitive

                nozzle = nozzle_from_primitive_address(primitive, address1)
                nozzle_offset = offset_for_nozzle(nozzle)

                #print("Offset for {} = {}".format(nozzle, nozzle_offset))

                fire_with_offset(nozzle_offset)

            primitives = primitives_from_bitmask(firing2)

            #print primitives

            for primitive in primitives:
                #print primitive

                nozzle = nozzle_from_primitive_address(primitive, address2)
                nozzle_offset = offset_for_nozzle(nozzle)

                #print("Offset for {} = {}".format(nozzle, nozzle_offset))

                #fire_with_offset(nozzle_offset)

    """
    maximum = 0

    for y in xrange(height):
        for x in xrange(width):
            if matrix[x, y][0] > maximum:
                maximum = matrix[x, y][0]
    """
    """scale = 255.0 / maximum_value

    for y in xrange(height):
        for x in xrange(width):
            matrix[x, y] = (255 - int(matrix[x, y][0] * scale), matrix[x, y][1], matrix[x, y][2], 255)
"""
    size = (width / 10, height / 10)
    #out.thumbnail(size, Image.ANTIALIAS)
    out.save('out.png')
