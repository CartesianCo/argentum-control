#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington

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

from PIL import Image
from cartridges import HP40Cartridge
from imagePreProcessing import getImages
from printers import argentum_v1_2

from simulator import simulateGUI

import sys

# Hash define equivalents for passing a value
X_AXIS = 0
Y_AXIS = 1

def writeMoveCmd(axis, steps, outputStream):
    if axis == X_AXIS:
        axis = 'X'
    else:
        axis = 'Y'
    outputStream.write('M {} {}\n'.format(axis, steps).encode('utf-8'))

def writeImageSize(size, outputStream):
    outputStream.write('S {} {}\n'.format(size[0], size[1]).encode('utf-8'))

def mirrorNibble(inputNibble):
    '''
    Takes in a nibble (4 bits) and returns the mirror.
    For example: mirrorNibble(0b0010) = 0b0100
    '''
    outputNibble =  (inputNibble & 0b00000001) << 3
    outputNibble |= (inputNibble & 0b00000010) << 1
    outputNibble |= (inputNibble & 0b00000100) >> 1
    outputNibble |= (inputNibble & 0b00001000) >> 3
    return outputNibble

def getFireCmd(address, firings, useTextualFiring):
    # The multiplexer doesn't have the first output connected to prevent issues
    # during startup.
    address += 1

    # The address is then mirrored because the electronics connections have this artifact
    # as an error in design.
    address = mirrorNibble(address)

    if useTextualFiring:
        return ('F {:01X}{:02X}{:02X}\n'.format(address, firings[0], \
                                                              firings[1]).encode('utf-8'))
    else:
        outpuStr = (chr(1)) # Fire command
        outpuStr += (chr(firings[0])) # Relevant firing data, i.e. which primitive(s) to fire
        outpuStr += (chr(address)) # The address we're firing within the primitive(s)
        outpuStr += ('\n')
        outpuStr += (chr(1)) # Fire command
        outpuStr += (chr(firings[1])) # Relevant firing data, i.e. which primitive(s) to fire
        outpuStr += (chr(address)) # The address we're firing within the primitive(s)
        outpuStr += ('\n')
        return outputStr

def writeFireCmd(address, firings, useTextualFiring, outputStream):

    cmdStr = getFireCmd(address, firings, useTextualFiring)
    outputStream.write(cmdStr)
    


def getSteps(error, displacement, stepsPerPixel):
    '''
    Input: Position error (image px), displacement required (image px), stepsPerPixel
    Output: New position error after move, steps required for move
    This function allows you to calculate the steps required to move to a new pixel position.
    This is a difficult problem because step and pixel distances are not perfectly divisible.
    There will always be an error in the movement.  Using this method enures that error is
    the minimum it can possibly be.  Using this method, the error will never go above 15%.
    '''
    # This is the first guess for the number of steps, it simply scales the displacement into
    # steps and rounds the answer
    newSteps = round(displacement * stepsPerPixel)
    oldSteps = newSteps
    # This is the error of taking 'newSteps' to achieving a movement of 'displacement'
    stepError = (newSteps / stepsPerPixel) - round(newSteps / stepsPerPixel)

    # This is the total error, after considering the current error already in the system.
    newError = error + stepError
    oldError = 1000

    # Now we iterate honing down in on a step size until we find the point where the error
    # begins growing again.
    while (abs(oldError) > abs(newError)):
        # If we reach here, it means the last iteration achieved a better result, replace
        # oldSteps and oldError with the better estimate.
        oldSteps = newSteps
        oldError = newError
        # If the error is positive, try stepping one step back and vice versa.
        if (newError) > 0:
            newSteps = oldSteps - 1
        else:
            newSteps = oldSteps + 1
        # Calculate the new step error and then add it to the original error for re-evaluation
        # note that if this value is NOT better, the while loop breaks and the 'old' values
        # are passed through, discarding these 'new' values.
        stepError = (newSteps / stepsPerPixel) - round(newSteps / stepsPerPixel)
        newError = error + stepError

    # In case there's some math error somewhere - this should never be invoked.
    if (displacement != int(round(oldSteps/stepsPerPixel))):
        print "Math Error"
    
    return (oldError, int(oldSteps))


def calcAddressFiringByte(bitmap, coverageData, bitmapSize, maxCoverage, x, y, cartridge, \
                          address):
    '''
    This Function takes in a two-tone image (as a 2D array), a position of the first nozzle
    in the cartridge and a cartridge address.  It returns a byte of information that
    dictates what primitives will fire in order to create the pixels desribed in bitmap.
    '''

    # If the bitmap is empty, return error code -1
    if (bitmap == None):
        return -1
    
    # Creates the output byte, ready for filling
    outputByte = 0

    # We need to determine whether the pixel in bitmap is turned on for each primitive in
    # the cartridge
    for primitive in range(cartridge.numPrimitives):
        # This is the displacement of the nozzle (defined by address, primitive) from the
        # first nozzle in the cartridge.
        nozzleDisplacement = cartridge.nozzleDisplacement(address, primitive)

        # This displacement is then used to offset from the given position of the first
        # nozzle
        nozzleX = x + nozzleDisplacement[0]
        nozzleY = y + nozzleDisplacement[1]

        # Check to see if the pixel extends beyond the bounds of the image.  This can occur
        # when one cartridge (or even just one column) is over the print area but the other
        # is not.  Therefore just insert a 'no fire' command and continue to the next nozzle.
        if (nozzleX < 0) or (nozzleY < 0) or (nozzleX >= bitmapSize[0]) \
                                              or (nozzleY >= bitmapSize[1]):
            continue
        
        # If the pixel is black in the image AND the current number of droplets already fired
        # at it is less than the coverage ratio - add a command to the output byte to fire the
        # given primitive.
        if (bitmap[nozzleX, nozzleY] != 1) and (coverageData[nozzleX, nozzleY] < maxCoverage):
            # This simply sets the bit in our outputByte for the corresponding primitive.
            outputByte += (1 << primitive)
            coverageData[nozzleX, nozzleY] += 1
    return outputByte


class ImageProcessor:

    # The resolution of the input image in DPI.
    stdImageRes = 600

    # Cartridge class object being processed for.
    cartridge = HP40Cartridge()

    # Printer class being processed for
    printer = argentum_v1_2()

    # Tuple (horizontal, vertical) offset from left to right cartridge.
    cartridgeOffset = (726, 0)

    # Minimum step size of the gantry system in mm.
    # 2.5mm per tooth, 16 teeth per pulley revolution -> (2.5 * 16)mm/rev
    # 200 steps per revolution, 16 micro-steps per step -> (200 * 16)steps/rev
    # ((2.5 * 16) / (200 * 16))mm/step
    minStep = (2.5 * 16) / (200 * 16)

    # The pixel count the ascorbic image will be expanded by.  By dilating the image
    # for the ascorbic cartridge, you can account for mild misalignments between the
    # print heads.
    stdAscorbicDilation = 3

    # The ratio of coverage applied to a particular pixel.
    # For example, if you want to have each pixel printed (with both cartridges) 3 times,
    # this number will be 3. This is achieved by advancing the carriage less than a full
    # swath between each pass and so prints over the same pixels again but with a different
    # set of nozzles.
    stdCoverageRatio = 3

    # This is the threshold value for the conversion of the image to a 1 bit bitmap.
    stdThreshold = 190

    # Current position of carriage relative to 0,0 of image IN IMAGE PIXELS
    xPos = 0
    yPos = 0

    # Current misalignment of printhead to actual pixel location to due the imperfect
    # divisibility of pixels to the minStep size.
    xError = 0.0
    yError = 0.0

    def __init__(self,cartridge=None,printer=None,cartridgeOffset=None,minStep=None,\
                 stdAscorbicDilation=None,stdCoverageRatio=None,stdImageRes=None,\
                 stdThreshold=None):

        if stdAscorbicDilation:
            self.stdAscorbicDilation = stdAscorbicDilation

        if stdCoverageRatio:
            self.stdCoverageRatio = stdCoverageRatio
        
        if cartridgeOffset:
            self.cartridgeOffset = cartridgeOffset

        if stdThreshold:
            self.stdThreshold = stdThreshold
        
        if stdImageRes:
            self.stdImageRes = stdImageRes

        if cartridge:
            self.cartridge = cartridge

        if printer:
            self.printer = printer
            
        if minStep:
            self.minStep = minStep

        
    def processImageForPrinting(self, inputImage, outputStream, progressFunc=None, size=None,\
                                ascorbicDilation=None, coverageRatio=None, imageRes=None,\
                                threshold=None):
        '''
        image:              PIL image object of the image to be processed.
        progressFunc:       function used to send progress updates out and cancel cmds in.
                            Eg. if not (progressFunc(itemsProcessed, totalItemsToProcess)):
                                    cancelProcessing()
        size:               New pixel dimensions required for image to be scaled to.
        ascorbicDilation:   The pixel count this ascorbic image will be expanded by.
        coverageRatio:      The ratio of coverage applied to a particular pixel in this image.
        threshold:          The threshold value for the 1 bit conversion of the image.
        imageRes:           The resolution of the input image in DPI.
        '''

        if ascorbicDilation:
            self.ascorbicDilation = ascorbicDilation
        else:
            self.ascorbicDilation = self.stdAscorbicDilation

        if coverageRatio:
            self.coverageRatio = coverageRatio
        else:
            self.coverageRatio = self.stdCoverageRatio

        if threshold:
            self.threshold = threshold
        else:
            self.threshold = self.stdThreshold

        if imageRes:
            self.imageRes = imageRes
        else:
            self.imageRes = self.stdImageRes

        # The side dimension of a single pixel in the image, given it's resolution
        self.imagePixelSize = 25.4 / self.imageRes
        
        # The number of steps per pixel in the image, given the step size.
        self.stepsPerPixel = self.imagePixelSize / self.minStep
        
        # This is the distance (in image pixels) the carriage advances after printing
        # each swath.  It is calculated using the swath height of the cartridge over the
        # coverage ratio times the image pixels per native cartridge pixels.  Hence if the
        # coverage ratio is 1 and the ratio of image pixels to native pixels is 2, the
        # carriage will advance half of the swath height.  Because there are twice as many
        # image pixels as native cartridge pixels, the odd or even rows are only printed on
        # in every second swath and are therefore only printed once.
        self.feedAdvance = (self.cartridge.swathHeight / (self.coverageRatio \
                            * self.cartridge.imagePxPerNativePx))
        
        # This ensures that the feed advance is an odd number.  This technically is only
        # needed when the image resolution is double the native cartridge resolution and
        # does NOT account for different ratios.
        if (self.feedAdvance % 2) == 0:
            self.feedAdvance -= 1

        # Use the preproccessor to scale, convert to 1-bit, dilate and crop whitespace from
        # the input image.
        # NOTE: the ascorbic acid image is dilated slightly to increase coverage and account
        # for small cartridge misalignments.
        silverImage, ascorbicImage, cropBoundingBox, pixelCounts = \
                     getImages(inputImage, self.threshold, self.ascorbicDilation, size=size)
        # Generate pixel access objects for the images
        silverData = silverImage.load()
        ascorbicData = ascorbicImage.load()
        # Uncomment these line to view the silverImage and ascorbicImage respectively
        # silverImage.show()
        # ascorbicImage.show()
        
        # This is a grayscale image bitmap generated to track the amount of droplets that have
        # been fired at a given pixel.  This is used to prevent swathAdvance banding.
        silverCoverage = Image.new("L", silverImage.size, 0)
        silverCoverageData = silverCoverage.load()
        ascorbicCoverage = Image.new("L", ascorbicImage.size, 0)
        ascorbicCoverageData = ascorbicCoverage.load()

        # The horizontal position that the first nozzle of the LHS cartridge will begin
        # printing relative to the top-left pixel of the image.  Note that there is an offset
        # because nozzle 1 (our printing origin) is on the LHS nozzle column and the LHS
        # cartridge. Therefore we shift to the left so that the RHS column of the RHS
        # cartridge is over the top left pixel.
        # startingXPos = -self.cartridgeOffset[0] - self.cartridge.columnOffset
        # startingXPos = -self.cartridgeOffset[0] + cropBoundingBox[0]
        startingXPos = -self.cartridgeOffset[0]
        # The vertical position that the first nozzle of the LHS cartridge will begin
        # printing relative to the top-left pixel of the image.  Note that there is an offset
        # upward because we only want the height of the feedAdvance over the top edge of the
        # image.  Therefore we move up (-ve) the swathHeight and then down the feedAdvance.
        startingYPos = self.feedAdvance - self.cartridge.swathHeight + cropBoundingBox[1]
        startingYPos = self.feedAdvance - self.cartridge.swathHeight
        # We also need to account for mis-alignment vertically in the print heads.
        if (self.cartridgeOffset[1] > 0):
            startingYPos -= self.cartridgeOffset[1]

        # The horizontal and vertical positions that the first nozzle of the LHS cartridge
        # will finish printing relative to the top-left pixel of the image.
        # endingXPos = image.size[0]
        endingXPos = image.size[0] + self.cartridge.columnOffset
        endingYPos = image.size[1] - self.feedAdvance
        # We also need to account for mis-alignment vertically in the print heads.
        if (self.cartridgeOffset[1] < 0):
            endingYPos -= self.cartridgeOffset[1]

        # If the ending vertical position does not provide an even divisor of the feedAdvance,
        # then add on some extra pixels until it is.
        endingYPos += (endingYPos - startingYPos) % self.feedAdvance

        # Fills an array with all of the horizontal positions that will be traversed by the
        # carriage.
        xVals = []
        cnt = startingXPos
        while cnt <= endingXPos:
            xVals.append(cnt)
            cnt += 1
        
        # Fills an array with all of the vertical positions that will be traversed by the
        # carriage.  Note that this is much less than the image height as each movement has a
        # value of self.feedAdvance.
        yVals = []
        cnt = startingYPos
        while cnt <= endingYPos:
            yVals.append(cnt)
            cnt += self.feedAdvance

        # This is the number of swaths that will result from the parameters above.
        # Note that it is '+1' at the end because you start at the beginning of the first
        # yPos and end at the end of the last yPos.
        # ALTERNATE CALC: numSwaths = (endingYPos - startingYPos) / self.feedAdvance + 1
        numSwaths = len(yVals)

        writeImageSize(silverImage.size ,outputStream)

        # Move the carriage to the starting position
        self.moveCommand(X_AXIS, startingXPos, outputStream)
        self.moveCommand(Y_AXIS, startingYPos, outputStream)

        # For each new swath
        swathsProcessed = -1
        for y in yVals:
            swathsProcessed += 1
            if progressFunc:
                if not(progressFunc(swathsProcessed, numSwaths)):
                    return
            else:
                percentage = int(float(swathsProcessed) / numSwaths * 100)
                print "{:d}% Image Processing Complete".format(percentage)

            swathString = ""
            emptySwath = True
            # For each horizontal position in the swath
            for x in xVals:
                emptyPosition = True
                positionStr = ""
                # Calculate the firings for this position for all addresses.
                for address in range(self.cartridge.numAddresses):
                    silverFiring = calcAddressFiringByte(\
                        silverData, silverCoverageData, silverImage.size, self.coverageRatio,\
                        x, y, self.cartridge, address)
                    ascorbicX = x + self.cartridgeOffset[0]
                    ascorbicY = y + self.cartridgeOffset[1]
                    ascorbicFiring = calcAddressFiringByte(\
                        ascorbicData, ascorbicCoverageData, ascorbicImage.size, \
                        self.coverageRatio, ascorbicX, ascorbicY, self.cartridge, address)

                    if (silverFiring != 0) and (ascorbicFiring != 0):
                        emptyPosition = False
                        emptySwath = False
                    
                    writeFireCmd(address, [silverFiring, ascorbicFiring], True, outputStream)
                
                self.moveCommand(X_AXIS, 1, outputStream)
                
            # After the swath has finished, move the carriage back to the starting position.
            self.moveCommand(X_AXIS, (startingXPos - self.xPos), outputStream)
            # Advance the carriage to the next swath position vertically.
            self.moveCommand(Y_AXIS,self.feedAdvance, outputStream)
        self.moveCommand(Y_AXIS, (startingYPos - self.yPos), outputStream)
            

    def moveCommand(self, axis, displacement, outputStream):
        if axis == X_AXIS:
            self.xPos += displacement
            self.xError, steps = getSteps(self.xError, displacement, self.stepsPerPixel)
            writeMoveCmd(axis, steps, outputStream)
        elif axis == Y_AXIS:
            self.yPos += displacement
            self.yError, steps = getSteps(self.yError, displacement, self.stepsPerPixel)
            writeMoveCmd(axis, steps, outputStream)
        else:
            print "ERROR"


if __name__ == "__main__":

    outputFileName = 'testCommands.HEX'
    fileStream = open(outputFileName, 'w')
    image = Image.open("textTest.png")
    #image = Image.open("INPUT.JPG")
    imProc = ImageProcessor()
    imProc.processImageForPrinting(image, fileStream, threshold=50, ascorbicDilation=5,\
                                   coverageRatio=2)
    fileStream.close()

    simulateGUI(outputFileName)







