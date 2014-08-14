
# Import Libraries
from PIL import Image          # image processing library 
import os             # library for handling actions like changing directory
import tkMessageBox, tkFileDialog
from Tkinter import Tk

# Define Constants
HEADOFFSET = 1365        # Distance between the same line of primitives on two different heads (in pixels)
PRIMITIVEOFFSET = 12     # Distance between two different primitives on the same head (in pixels)
VOFFSET = 0              # Vertical distance between the two printheads
SPN = 3.386666           # Steps per nozzle (actually per half nozzle as we are doing 600 dpi)

# Movement offset in pixels. This is how far down we move between lines. 
# Can be changed to any odd number less than 103. A larger number means the
# print will be faster but put down less ink and have less overlap
mOffset = 41

# Firings per step variable. Currently cannot set different firings per step for
# different print heads but this will be implemented very soon - won't take me 
# long to implement.
fps = 1

NOZZLES_PER_PRIMITIVE = 13
ALL_PRIMITIVES = 0b11111111
ODD_PRIMITIVES = 0b10101010
EVEN_PRIMITIVES = 0b01010101
NUMBER_OF_FIRINGS = 25
STEPS_PER_NOZZLE = 1

outputStream = open('Output.hex', 'wb')

def flipAddress(a):
    print 'Before: {:04b}'.format(a + 1)
    
    address = 0
    
    address = address | ((a + 1) & 0b00000001) << 3
    address = address | ((a + 1) & 0b00000010) << 1
    address = address | ((a + 1) & 0b00000100) >> 1
    address = address | ((a + 1) & 0b00001000) >> 3
    
    print 'After: {:04b}'.format(address)
    
    return address

def firingCommand(address, firing):
    shiftedFiring = 1 << firing
        
    print 'Primitives: {:08b}, Nozzle: {:013b}\n'.format(address, shiftedFiring)
    
    #return
    
    #address = flipAddress(address)
    firing = flipAddress(firing)
    
    outputStream.write(chr(1)) # Fire command
    outputStream.write(chr(address)) # The address we are firing on
    outputStream.write(chr(firing)) # Relevant firing data, i.e. which primitive to fire
   
    outputStream.write(chr(0))
    
def relativeMovementCommand(relativeMovement):
    if relativeMovement == 0:
        return
        
    move = (relativeMovement * STEPS_PER_NOZZLE)
    
    print 'M X {}\n'.format(move)
    
    #return
    
    outputStream.write('M X %d\n' % move)

def addressForOddNozzleIndex(index):
    if index < 0 or index > 12:
        index = index % NOZZLES_PER_PRIMITIVE
    
    address = 1 + (index * 4)
    
    address = (address % NOZZLES_PER_PRIMITIVE)
    
    # This is because of the modulus, we can never have an actual
    # value of zero here (because our address lines are offset)
    # in the multiplexer hardware, so this should be fine
    if address == 0:
        address = 13
    
    return address

def addressForEvenNozzleIndex(index):
    return addressForOddNozzleIndex(index + 4)

# Sequence
#
# Sit still, and fire every nozzle in that column
#
# For each nozzle in the EVEN primitives
#   fire and step
#   repeat this 100 (?) times
#
# Repeat above for ODD primitives
#

"""
    for i in xrange(NUMBER_OF_FIRINGS):
        for nozzle in xrange(13):
            
            address = 0b00000001
            
            for z in xrange(4):
                
                firingCommand(address, nozzle)
                firingCommand(0, 0)
                
                address = address << 2
            
        relativeMovementCommand(2)
"""
    
def main():
    address = 0b00000001
    
    for nozzle in xrange(13):
        
        for i in xrange(NUMBER_OF_FIRINGS):
            
            address = 0b00000001
        
            for z in xrange(4):
            
                firingCommand(address, addressForEvenNozzleIndex(nozzle))
                firingCommand(0, 0)
            
                relativeMovementCommand(2)
            
                address = address << 2

    outputStream.flush()
    outputStream.close()
    
    return
    
    yposition = 0
    
    for y in range(height/mOffset*2 + 1):
        
        # Print out progress
        print '{} out of {}.'.format(y + 1, height/mOffset*2 + 1)    
        
        move = 0
        xposition = 0
        
        # Iterate through the width of the image(s)
        for x in range(width):
            
            firings = [[calculateFiring(x, y, a, 0), calculateFiring(x, y, a, 1)] for a in range(13)]
            
            # if not any([any(firings[i]) for i in range(len(firings))]):
            #     #move += (int((x + 1) * SPN) - xposition - move)
            #     move = (int((x + 1) * SPN) - xposition)
            #     continue
            # elif move != 0:
            #     xposition += move
            #     outputStream.write('M X %d\n' % move)
            #     move = (int((x + 1) * SPN) - xposition)

            if any([any(firings[i]) for i in range(len(firings))]):
                if move != 0 :
                    xposition += move
                    outputStream.write('M X %d\n' % move)

            move = (int((x + 1) * SPN) - xposition)
                
            for f in range(fps):
                # Iterate through addresses
                for a in range(13):
                    if firings[a] == [0, 0]: 
                        continue
                    
                    for i in range(2):
                        #outputStream.write(chr(1))
                        #outputStream.write(chr(firings[a][i]))
                        #outputStream.write(chr(a + 1))
                        #outputStream.write(chr(0))


                        # NOTE: I don't think this will work correctly, pretty sure it should be OR instead of ADDITION
                        # NOTE: turns out that addition will give the same result as or, as long as the bits you're adding don't cause an overflow
                        # i.e. none of them are already set.
                        address = ((a + 1) & 0b00000001) << 3
                        address += ((a + 1) & 0b00000010) << 1
                        address += ((a + 1) & 0b00000100) >> 1
                        address += ((a + 1) & 0b00001000) >> 3
                        # aa = a + 1
                        # address = 0
                        #
                        # address |= ((aa & 0b0001) << 3)
                        # address |= ((aa & 0b0010) << 1)
                        # address |= ((aa & 0b0100) >> 1)
                        # address |= ((aa & 0b1000) >> 3)
                        
                        if 1 == 1:
                            #outputStream.write(chr(1)) # Fire command
                            #outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                            #outputStream.write(chr(address)) # The address we are firing on
                            #outputStream.write(chr(0))
                            outputStream.write('Firing for {:n}: {:08b}, address: {:013b}\n'.format(i, firings[a][i], address))
                        
                        if 1 == 0:
                            
                            if y % 4 == 0:      
                                outputStream.write(chr(1)) # Fire command
                                outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                                outputStream.write(chr(address)) # The address we are firing on
                                outputStream.write(chr(0))
                        
        
        # Move back
        #print xposition
        #if xposition != 0:
            #outputStream.write('M X %d\n' % -xposition)
            #print xposition
            #xposition = 0
        if xposition != 0:    
            outputStream.write('M X 0\n')
            xposition = 0
        
        # Move down
        
        movey = int(mOffset * (y + 1) * SPN) - yposition
        outputStream.write('M Y %d\n' % -movey)
        yposition += movey
        

    # Reset X and Y positions

    outputStream.write('M Y 0\n')
    outputStream.write('M X 0\n')

    
   
    
    outputStream.close()
    
    

def calculateFiring(xPos, yPos, addr, side):
    # Lookup tables to convert address to position
    positions = ((0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3), (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12))

    # 13 nozzles in a primitive, these are the number of the nozzles, in the correct firing order.
    # the second grouping is for the even side? it is simply offset by the first 3 nozzles, which is strange.
    # I would have assumed it to be just the reverse of the first one, to maintain maximum physical distance between firing nozzles.
    
    # The second one IS for the even side, and by shifting the order 3 settings, you can use the same index to get the
    # correct firing for each primitive.
    
    firing = 0
    
    x = xPos
    y = (yPos * mOffset)/2 + (positions[0][addr] * 2)
    if yPos % 2: y += 1    
    for i in range(4):
        if pixelMatrices[side*2][x, y][2] <= 200:
            firing |= 1 << (i*2)
            #print 'firing A -> x {}, y {}, addr {}, i {}'.format(x, y, addr, i)
        y += 26
    
    y = (yPos * mOffset)/2 + (positions[1][addr] * 2)
    if yPos % 2: y += 1
    for i in range(4):
        if pixelMatrices[side*2 + 1][x, y][2] <= 200:
            firing |= 1 << (i*2 + 1)
            #print 'firing B -> x {}, y {}, addr {}, i {}'.format(x, y, addr, i)
        y += 26

    if(firing):
        print 'Calculating Primitives to fire for ({}, {}), address: {:#013b}, side: {}'.format(xPos, yPos, addr, side)
        
    return firing

if __name__ == '__main__':
    main()
