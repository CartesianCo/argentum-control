
# Import Libraries
from PIL import Image          # image processing library
import os             # library for handling actions like changing directory
import tkMessageBox, tkFileDialog
from Tkinter import Tk
import math
from CartesianCo import HP_CC

cartridge = HP_CC()

NUMBER_OF_FIRINGS = 12
STEPS_PER_NOZZLE = 1

outputStream = open('Output.hex', 'wb')

def flipAddress(a):
    #print 'Before: {:04b}'.format(a + 1)

    address = 0

    address = address | ((a + 1) & 0b00000001) << 3
    address = address | ((a + 1) & 0b00000010) << 1
    address = address | ((a + 1) & 0b00000100) >> 1
    address = address | ((a + 1) & 0b00001000) >> 3

    #print 'After: {:04b}'.format(address)

    return address

def firingCommand(address, firing):
    c = 0
    ad = address
    while(ad > 0):
        c = c + 1
        ad = ad >> 1

    if address > 0 and firing > 0:
        print 'Primitives: {:02} - {:02}, Address: {:02}'.format(address, c, firing)
        print 'Primitives: {:08b}, Address: {:014b}'.format(address, (1 << firing))

    #return

    firing = flipAddress(firing)

    outputStream.write(chr(1)) # Fire command
    outputStream.write(chr(address)) # The address we are firing on
    outputStream.write(chr(firing)) # Relevant firing data, i.e. which primitive to fire
    outputStream.write(chr(0))

def moveX(distance):
    moveCommand('X', distance)

def moveY(distance):
    moveCommand('Y', distance)

def moveCommand(direction, distance):
    #if distance == 0:
    #    return

    if not (direction == 'X' or direction == 'Y'):
        print('Bad Direction Value {}'.format(direction))
        return

    move = (distance * STEPS_PER_NOZZLE)

    command = 'M {} {}\n'.format(direction, move)

    print(command)
    outputStream.write(command)

def fireNozzleByPrimitiveIndex(c, primitive, index):
    # Address for this nozzle
    address = cartridge.addressForPrimitiveIndex(primitive, index)

    #print('Address: {}'.format(address))

    if c == 0:
        firingCommand((1 << primitive), address)
        firingCommand(0, 0)
    else:
        firingCommand(0, 0)
        firingCommand((1 << primitive), address)

    #var = (1 << primitive)
    #print 'Var: {}'.format(var)

    print 'Primitive: {}, Index: {}, Address: {}'.format(primitive, index, address)

def fireNozzle(c, nozzle):
    # What primitive is the nozzle in?
    primitive = cartridge.primitiveForNozzle(nozzle)

    # What index within that primitive is this nozzle?
    index = cartridge.indexForNozzle(nozzle)

    print('Nozzle: {} -> Primitive: {}, Index: {}'.format(nozzle, primitive, index))
    fireNozzleByPrimitiveIndex(c, primitive, index)

def fireEvenColumn(c):
    for i in xrange(52):
        fireNozzle(c, (i * 2) + 1)

def fireOddColumn(c):
    for i in xrange(52):
        fireNozzle(c, i * 2)

def firePrimitive(primitive):
    for index in xrange(13):
        fireNozzleByPrimitiveIndex(c, primitive, index)

def fireLine(c):
    for i in xrange(10):
        fireOddColumn(c)

    moveX(40)

    for i in xrange(10):
        fireEvenColumn(c)

def main():
    scale = 10

    for c in xrange(2):
        for a in xrange(2):
            for primitive in xrange(4):
                fireLine(c)

                for index in xrange(13):
                    for x in xrange(NUMBER_OF_FIRINGS):
                        fireNozzleByPrimitiveIndex(c, (primitive * 2) + a, index)
                        moveX(3)

        fireLine(c)

    moveX(0)
    moveY(1000)

    outputStream.flush()
    outputStream.close()

    return

if __name__ == '__main__':
    main()
