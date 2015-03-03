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

'''
This module is designed to pre-process images that are to be used for generating inkjet
printing code from.  Essentially the only function that should be imported for use is the
getImages function which performs all intermediate steps in preparing an image.
'''

from PIL import Image

OFF = 1
ON = 0

def dilate(inputImage, dilateCount):
    '''
    This function takes in a PIL image file and then uses a simple nearest neighbour
    algorithm to expand the data by 1 pixel.  This is effectively the opposite function
    as eroding an image.
    NOTE: this function denotes a bit to be 'set' if it is black, ie it's value is 0.
    '''

    # This is a recursion breaker.  This function will recursively invoke itself until
    # dilateCount = 0.
    if (dilateCount <= 0):
        return inputImage

    # Simply assigning the width and height their own variables.
    width, height = inputImage.size
    # Generating a copy for the output image from the original.
    outputImage = inputImage.copy()
    # This generates a pixel access object (essentially a 2D array of the pixels)
    inputArray = inputImage.load()
    outputArray =  outputImage.load()

    # For each column of pixels
    for x in range(width):
        # For each pixel in the column
        for y in range(height):
            # If the pixel is already set, continue to the next pixel.
            if inputArray[x, y] == ON:
                continue
            # If the pixel is not on the left edge and a pixel to the left is set,
            # then set this pixel and continue to the next.
            if x > 0 and inputArray[x - 1, y] == ON:
                outputArray[x, y] = ON
                continue
            # If the pixel is not on the right edge and a pixel to the right is set,
            # then set this pixel and continue to the next.
            if x < width - 1 and inputArray[x + 1, y] == ON:
                outputArray[x, y] = ON
                continue
            # If the pixel is not on the top edge.
            if y > 0:
                # If the pixel is not on the left edge and a pixel to the NW is set,
                # then set this pixel and continue to the next.
                if x > 0 and inputArray[x - 1, y - 1] == ON:
                    outputArray[x, y] = ON
                    continue
                # If the pixel above is set, then set this pixel and continue to the next.
                if inputArray[x, y - 1] == ON:
                    outputArray[x, y] = ON
                    continue
                # If the pixel is not on the right edge and a pixel to the NE is set,
                # then set this pixel and continue to the next.
                if x < width - 1 and inputArray[x + 1, y - 1] == ON:
                    outputArray[x, y] = ON
                    continue
            if y < height - 1:
                # If the pixel is not on the left edge and a pixel to the SW is set,
                # then set this pixel and continue to the next.
                if x > 0 and inputArray[x - 1, y + 1] == ON:
                    outputArray[x, y] = ON
                    continue
                # If the pixel below is set, then set this pixel and continue to the next.
                if inputArray[x, y + 1] == ON:
                    outputArray[x, y] = ON
                    continue
                # If the pixel is not on the right edge and a pixel to the SE is set,
                # then set this pixel and continue to the next.
                if x < width - 1 and inputArray[x + 1, y + 1] == ON:
                    outputArray[x, y] = ON
                    continue
    # OutputArray edits the data stored by the pointer outputImage, therefore all
    # the data is retained within outputImage
    return dilate(outputImage, dilateCount - 1)

def toOneBitBmp(inputImage, threshold):
    '''
    Takes an input image in arbitrary color mode and uses simple thresholding to convert
    to a 1 bit bitmap image.  Ie. the output image will only have 1 bit of information
    per pixel, either on or off.
    '''
    # This is the simple way of doing it with the PIL library but it is not configurable.
    # return inputImage.convert('1')

    # This is a configurable threshold function that converts to greyscale and then to 1 bit.
    outputImage = inputImage.convert('L')
    return outputImage.point(lambda x: x >= threshold, '1')

def resizeImage(inputImage, size):
    '''
    Takes an input image, resizes it to size using the PIL NEAREST algorithm
    '''
    return inputImage.resize(size, Image.NEAREST)

def countPixels(inputImage):
    '''
    Counts the number of 'on' pixels ina given image and returns that value.
    '''
    # Generates pixel access for image.
    data = inputImage.load()
    # Assigns width and height for easier access.
    width, height = inputImage.size
    # Initialize number of pixels in the image as 0.
    numPixels = 0

    # For each column in the image.
    for x in range(width):
        # For each row in the image.
        for y in range(height):
            # If the pixel is 'on'.
            if data[x,y] == ON:
                # Increment the number of pixels in the image.
                numPixels += 1

    return numPixels

def cropImage(inputImage):
    '''
    Takes an input image, determines the bounding box of the actual data, crops the image
    using this and then returns a tuple of (croppedImage, bounding box)
    '''
    # Generates pixel access for image.
    data = inputImage.load()
    # Assigns width and height for easier access.
    width, height = inputImage.size

    # Initializing variables for the 4 bounding box values.
    minPixelX = width
    minPixelY = height
    maxPixelX = 0
    maxPixelY = 0

    # For each column in the image.
    for x in range(width):
        # For each row in the image.
        for y in range(height):
            # If the pixel is 'on'.
            if data[x,y] == ON:
                # Update the bounding box variables if appropriate.
                minPixelX = min(x, minPixelX)
                maxPixelX = max(x, maxPixelX)
                minPixelY = min(y, minPixelY)
                maxPixelY = max(y, maxPixelY)

    # If the max value is higher than the min value then some wires were crossed or the image
    # is empty.  Return an empty image.
    if maxPixelX < minPixelX or maxPixelY < minPixelY:
        print "ERROR: Input image is empty"
        return (Image.new("1",(0,0),1), (0,0))

    # Placing the bounding box variables in a tuple.
    boundingBox = (minPixelX, minPixelY, maxPixelX+1, maxPixelY+1)

    # Crop and return the image as well as the bounding box
    return inputImage.crop(boundingBox), boundingBox

def getCroppedImages(inputImage, dilation):
    '''
    Takes an image and pixel dilation value, returns two images with edge white space cropped,
    one having been dilated by 'dilation' pixels as well as the bounding box used and the
    number of pixels in each image as a tuple.
    NOTE: the bounding box is determined by the information in the dilated image.
    '''
    # First dilate the image.
    dilatedImage = dilate(inputImage, dilation)
    # Crop white space from the edges and store the bounding box.
    croppedDilatedImage, boundingBox = cropImage(dilatedImage)
    # Apply the same bounding box crop to the original image (as the dilated image will have
    # a larger bounding box.
    croppedImage = inputImage.crop(boundingBox)
    # Count the pixels used in each image.
    pixelCounts = (countPixels(croppedImage), countPixels(croppedDilatedImage))
    # Return the two images and the bounding ox used.
    return croppedImage, croppedDilatedImage, boundingBox, pixelCounts

def getImages(inputImage, threshold, dilation, size=None):
    '''
    Takes in a PIL image object, scales the image if a size is provided, converts it to a 1
    bit bitmap using 'threshold', generates a dilated image from 'dilation', crops white space
    from the edges of the dilated image and then applies the same bounding box to the original
    and then returns the both images as well as the crop bounding box used.
    '''
    # If a size is provided for scaling
    if size:
        # Scale the image
        inputImage = resizeImage(inputImage, size)
    # Convert the input image to a 1-bit bitmap using the given threshold.
    inputImage = toOneBitBmp(inputImage, threshold)
    # We now generate a new image that is expanded by 'dilation' pixels on all edges and
    # paste the image in the centre - this accounts for any dilation that would otherwise
    # extend past the borders of the image.
    newSize = (inputImage.size[0] + (2*dilation), inputImage.size[1] + (2*dilation))
    newImage = Image.new("1",newSize,1)
    newImage.paste(inputImage, (dilation, dilation))
    # Retrieve the cropped image as well as a dilated version of the cropped image and
    # as the bounding box used from the original image.
    return getCroppedImages(newImage, dilation)

if __name__ == "__main__":
    #image = Image.open("textTest.png")
    #image = Image.open("testImage3.bmp")
    image = Image.open("INPUT.JPG")
    image, dilatedImage, boundingBox, pixelCounts = getImages(image, 50, 1)
    print boundingBox
    print pixelCounts
    image.show()
    dilatedImage.show()
