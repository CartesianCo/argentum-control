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
from PyQt4.QtGui import QImage, QTransform
from PyQt4 import QtCore
import os
import sys
import time
### Image Processing Functions

"""
# Define Constants - RC1
HEADOFFSET = 726 # Distance between the same line of primitives on two different heads (in pixels)
PRIMITIVEOFFSET = 12 # Distance between two different primitives on the same head (in pixels)
VOFFSET = -2 # Vertical distance between the two printheads
"""

# Python 3 fail
try:
    xrange
except NameError:
    xrange = range

def calcDJB2(contents):
    hash = 5381
    for c in contents:
        cval = ord(c)
        if cval >= 128:
            cval = -(256 - cval)
        hash = hash * 33 + cval
        hash = hash & 0xffffffff
    return hash

class ImageProcessor:
    # Distance between the same line of primitives on two different heads (in pixels)
    # Distance between the two cartridges in pixels
    HEADOFFSET = 726

    # Distance between two different primitives on the same head (in pixels)
    # Distance between the two rows of nozzles
    PRIMITIVEOFFSET = 12

    # Vertical distance between the two printheads
    VOFFSET = 0

    # Steps per nozzle (actually per half nozzle as we are doing 600 dpi)
    SPN = 3.386666

    # Movement offset in pixels. This is how far down we move between lines.
    # Can be changed to any odd number less than 103. A larger number means the
    # print will be faster but put down less ink and have less overlap
    mOffset = 103

    # Number of dilation operations to perform on asorbic
    dilateCount = 3

    # Firings per step variable. Currently cannot set different firings per step for
    # different print heads but this will be implemented very soon - won't take me
    # long to implement.
    fps = 1

    outputFile = None

    # This allows for easier inspection of hex files
    USE_TEXTUAL_FIRING = True

    def __init__(self, horizontal_offset=None, vertical_offset=None, overlap=None, dilateCount=None):
        if horizontal_offset:
            self.HEADOFFSET = horizontal_offset

        if vertical_offset:
            self.VOFFSET = vertical_offset

        if overlap:
            self.mOffset = overlap

        if dilateCount != None:
            self.dilateCount = dilateCount

    def sliceImage(self, inputFileName, outputFileName, progressFunc=None, size=None):
        #directory = direct
        # Global variables to hold the images we are working with
        global outputImages
        global pixelMatrices

        start = time.time()

        outputImages = []
        pixelMatrices = []

        outputFile = open(outputFileName, 'wb')

        # Go to our working directory and open/create the output file
        #os.chdir(directory)
        #hexOutput = outputFile
        self.outputFile = outputFile
        self.outputFileName = outputFileName

        # Open our image and split it into its odd rows and even rows
        if type(inputFileName) == type(''):
            inputImage = QImage(inputFileName)
        else:
            inputImage = inputFileName
        if size:
            width, height = size
            inputImage = inputImage.scaled(width, height, aspectRatioMode=QtCore.Qt.IgnoreAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
        inputImage = inputImage.mirrored(horizontal=True, vertical=False)
        #rot270 = QTransform()
        #rot270.rotate(270)
        #inputImage = inputImage.transformed(rot270)
        rot90 = QTransform()
        rot90.rotate(90)
        inputImage = inputImage.transformed(rot90)

        print("after transformed {}".format(time.time() - start))
        start = time.time()

        inputs = self.splitImageTwos(inputImage)

        print("after splitImageTwos {}".format(time.time() - start))
        start = time.time()

        # Get the size of the input images and adjust width to be that of the output
        width, height = inputs[0].size
        width += self.HEADOFFSET + self.PRIMITIVEOFFSET

        # Adjust the height. First make sure it is a multiple of mOffset.
        height += (self.mOffset - height % self.mOffset)

        # Then add an extra 2 rows of blank lines.
        height += (104 * 2)

        # Create the output images and put them into a list for easy referencing
        outputImages = [
                Image.new('RGBA', (width , height), (255, 255, 255, 255))
                for i in range(4)
        ]

        # Paste the split input image into correct locations on output images

        # (0, VOFFSET + 104) = (0, 104)
        # (PRIMITIVEOFFSET, VOFFSET + 104) = (12, 104)

        pasteLocations = (
            (
                self.HEADOFFSET,
                int((int(208 / self.mOffset) * self.mOffset) / 2)
            ),
            (
                self.HEADOFFSET + self.PRIMITIVEOFFSET,
                int((int(208 / self.mOffset) * self.mOffset) / 2)
            ),
            (
                0,
                int((int(208 / self.mOffset) * self.mOffset) / 2 + self.VOFFSET)
            ),
            (
                self.PRIMITIVEOFFSET,
                int((int(208 / self.mOffset) * self.mOffset) / 2 + self.VOFFSET)
            )
        )

        inputs2 = inputs
        tot = 50 / self.dilateCount
        for i in range(self.dilateCount):
            inputs2 = [ self.dilate(inputs2[0]), self.dilate(inputs2[1]) ]
            if progressFunc:
                if not progressFunc((i + 1) * tot, 50 + tot):
                    return

        print("after dilute {}".format(time.time() - start))
        start = time.time()

        outputImages[0].paste(inputs[0], pasteLocations[0])
        outputImages[1].paste(inputs[1], pasteLocations[1])
        outputImages[2].paste(inputs2[0], pasteLocations[2])
        outputImages[3].paste(inputs2[1], pasteLocations[3])

        pixelMatrices = [
            outputImages[i].load()
            for i in range(4)
        ]

        print("after paste {}".format(time.time() - start))
        start = time.time()

        # We have our input images and their matrices. Now we need to generate
        # the correct output data.
        self.writeCommands(progressFunc)

        print("after write commands {}".format(time.time() - start))
        start = time.time()

    def dilate(self, img):
        width, height = img.size
        outImg = img.copy()
        inp = img.load()
        outp =  outImg.load()
        on = (0, 0, 0)
        for x in range(width):
            for y in range(height):
                if inp[x, y][2] <= 200:
                    continue
                if x > 0 and inp[x - 1, y][2] <= 200:
                    outp[x, y] = on
                    continue
                if x < width - 1 and inp[x + 1, y][2] <= 200:
                    outp[x, y] = on
                    continue
                if y > 0:
                    if x > 0 and inp[x - 1, y - 1][2] <= 200:
                        outp[x, y] = on
                        continue
                    if inp[x, y - 1][2] <= 200:
                        outp[x, y] = on
                        continue
                    if x < width - 1 and inp[x + 1, y - 1][2] <= 200:
                        outp[x, y] = on
                        continue
                if y < height - 1:
                    if x > 0 and inp[x - 1, y + 1][2] <= 200:
                        outp[x, y] = on
                        continue
                    if inp[x, y + 1][2] <= 200:
                        outp[x, y] = on
                        continue
                    if x < width - 1 and inp[x + 1, y + 1][2] <= 200:
                        outp[x, y] = on
                        continue
        return outImg

    def writeCommands(self, progressFunc=None):
        width, height = outputImages[0].size

        # Ignore empty pixels added to the bottom of the file.
        height -= (int(208/self.mOffset) * self.mOffset)

        xposition = 0

        for y in xrange(int(height/self.mOffset)*2 + 1):
            # Print out progress
            if progressFunc:
                if not progressFunc(y + 1, int(height/self.mOffset)*2 + 11):
                    self.outputFile.close()
                    os.remove(self.outputFileName)
                    return
            else:
                print('{} out of {}.'.format(y + 1, int(height/self.mOffset)*2 + 1))

            yposition = 0

            # Iterate through the width of the image(s)
            for x in xrange(width):

                firings = [
                        [
                            self.calculateFiring(x, y, a, 0),
                            self.calculateFiring(x, y, a, 1)
                        ]
                    for a in xrange(13)
                ]

                if not any([any(firings[i]) for i in xrange(len(firings))]):
                    continue

                move = int((x + 1) * self.SPN) - yposition
                if move != 0:
                    yposition += move
                    self.writeMovementCommand('Y', move)

                for f in xrange(self.fps):
                    # Iterate through addresses
                    for a in xrange(13):
                        if firings[a] != [0]:
                            self.writeFiringCommand(a, firings[a][0], firings[a][1])

            # Carriage return
            if yposition != 0:
                self.writeMovementCommand('Y', -yposition)
                yposition = 0

            # Line feed
            movex = int(self.mOffset * (y + 1) * self.SPN) - xposition
            self.writeMovementCommand('X', -movex)
            xposition += movex


        # Reset X and Y positions
        #self.writeMovementCommand('X', 0)
        #self.writeMovementCommand('Y', 0)

        self.outputFile.close()

    def calculateFiring(self, xPos, yPos, addr, side):
        # Lookup tables to convert address to position
        positions = (
            (0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3),
            (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12)
        )

        # 13 nozzles in a primitive, these are the number of the nozzles, in the
        # correct firing order. The second grouping is for the even side? it is
        # simply offset by the first 3 nozzles, which is strange. I would have
        # assumed it to be just; the reverse of the first one, to maintain
        # maximum physical distance between firing nozzles.

        # The second one IS for the even side, and by shifting the order 3
        # settings, you can use the same index to get the correct firing for
        # each primitive.

        firing = 0

        x = xPos

        # Calculate the y offset for the given address

        # odd side?
        y = (yPos * self.mOffset)/2 + (positions[0][addr] * 2)

        # ensure that yPos is even
        if yPos % 2:
            y += 1

        for i in range(4):
            # if this pixel is on, set the corresponding bit in firing
            if pixelMatrices[side*2][x, y][2] <= 200:
                firing += 1 << (i*2)
            y += 26


        y = (yPos * self.mOffset)/2 + (positions[1][addr] * 2)

        # ensure that yPos is even
        if yPos % 2:
            y += 1

        for i in range(4):
            # if this pixel is on, set the corresponding bit in firing
            if pixelMatrices[side*2 + 1][x, y][2] <= 200:
                firing += 1 << (i*2 + 1)
            y += 26

        return firing

    '''
    Splits an input image into two images.
    '''
    def splitImageTwos(self, image):
        width = image.width()
        height = image.height()

        # If the height of the input image isn't a multiple of 4, round it up.
        if height % 4 != 0:
            # (height % 4) will be the remainder left over
            # so 4 - remainder will be the difference required
            height += (4 - (height % 4))

        # New images to store the split rows. Each image has half the height,
        # since we're splitting the image vertically.
        odd = Image.new('RGBA', (width, int(height/2)), (255, 255, 255, 255))
        even = Image.new('RGBA', (width, int(height/2)), (255, 255, 255, 255))

        # References to the pixel data.
        evenMatrix = even.load()
        oddMatrix = odd.load()
        inputVector = image.bits()
        inputVector.setsize(image.byteCount())
        stride = width*4

        def inputMatrix(x, y):
            return (ord(inputVector[x*4   + y*stride]),
                    ord(inputVector[x*4+1 + y*stride]),
                    ord(inputVector[x*4+2 + y*stride]),
                    ord(inputVector[x*4+3 + y*stride]))

        # Divide by 4 because we're copying two rows at a time (why?)
        # Subtract 1 because of zero-offset.
        for y in xrange(int(height / 4) - 1):
            for x in xrange(width):
                oddMatrix[x, y*2] = inputMatrix(x, y*4)
                oddMatrix[x, y*2+1] = inputMatrix(x, y*4+1)

                evenMatrix[x, y*2] = inputMatrix(x, y*4+2)
                evenMatrix[x, y*2+1] = inputMatrix(x, y*4+3)

        # Handle the final row(s) specially
        # This shouldn't be necessary, since we know how many extras
        # (non-existant) we added.
        y = int(height / 4) - 1
        for x in xrange(width):
            if y*4 < image.height(): oddMatrix[x, y*2] = inputMatrix(x, y*4)
            if y*4 + 1 < image.height(): oddMatrix[x, y*2+1] = inputMatrix(x, y*4+1)

            if y*4 + 2 < image.height(): evenMatrix[x, y*2] = inputMatrix(x, y*4+2)
            if y*4 + 3 < image.height(): evenMatrix[x, y*2+1] = inputMatrix(x, y*4+3)

        return (odd, even)

    def writeMovementCommand(self, axis, steps):
        self.outputFile.write('M {} {}\n'.format(axis, steps).encode('utf-8'))

    def writeFiringCommand(self, a, firing1, firing2):
        # The multiplexer doesn't use the first output, for startup reasons.
        a = a + 1

        address =  (a & 0b00000001) << 3
        address += (a & 0b00000010) << 1
        address += (a & 0b00000100) >> 1
        address += (a & 0b00001000) >> 3

        #self.outputFile.write('F {} {} {}\n'.format(a, firing1, firing2))


        if self.USE_TEXTUAL_FIRING:
            self.outputFile.write('F {:01X}{:02X}{:02X}\n'.format(address, firing1, firing2).encode('utf-8'))
        else:
            outputStream = self.outputFile
            outputStream.write(chr(1)) # Fire command
            outputStream.write(chr(firing1)) # Relevant firing data, i.e. which primitive(s) to fire
            outputStream.write(chr(address)) # The address we're firing within the primitive(s)
            outputStream.write('\n')
            outputStream.write(chr(1)) # Fire command
            outputStream.write(chr(firing2)) # Relevant firing data, i.e. which primitive(s) to fire
            outputStream.write(chr(address)) # The address we're firing within the primitive(s)
            outputStream.write('\n')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: imageproc <image file> <hex file> [width height]")
        sys.exit(1)
    size = None
    if len(sys.argv) == 5:
        size = (int(sys.argv[3]), int(sys.argv[4]))
    ip = ImageProcessor()
    ip.sliceImage(sys.argv[1], sys.argv[2], size)
