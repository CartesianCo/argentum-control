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

from ImageTk import PhotoImage
from Tkinter import Tk, Canvas, Button, Scrollbar, Y, ALL, VERTICAL, HORIZONTAL

import sys
from math import sqrt

# Hash define equivalents for passing a value
X_AXIS = 0
Y_AXIS = 1

MOVE_CMD = 0
FIRE_CMD = 1
SIZE_CMD = 2

def zoomIn():
    global root
    root.zoom *= 1.5
    updateImage()

def zoomOut():
    global root
    root.zoom /= 1.5
    updateImage()

def updateImage():
    global root
    global images
    root.img = PhotoImage(images[root.index].resize((int(root.zoom * \
                                                         images[root.index].size[0]), \
                                                     int(root.zoom * \
                                                         images[root.index].size[1])),  \
                                                    Image.NEAREST))
    root.canvas.delete("all")
    width, height = images[root.index].size
    imageX = int((root.canvasSize[0] / 2) - (root.zoom * width / 2))
    imageY = int((root.canvasSize[1] / 2) - (root.zoom * height / 2))
    root.canvas.create_image(imageX,imageY,image=root.img, anchor="nw")
    root.canvas.config(scrollregion=root.canvas.bbox(ALL))

def nextImage():
    global root
    if root.index < root.maxIndex:
        root.index += 1
        updateImage()

def prevImage():
    global root
    if root.index > 0:
        root.index -= 1
        updateImage()

def determineSize(cmds, cartridge, cartridgeOffset, stepsPerPixel):
    '''
    Takes in an array of cmds (arranged as (cmdType, (tuple of information)),
    the class of cartridge used (eg. HP40Cartridge()),
    the offset from one cartriddge to the other (x, y) and
    the ratio of steps to image pixels.

    Returns the position in steps from the beginning position of the carriage to where
    the printed image actually begins (x, y) and
    the width and height of the actual printed image (in steps).
    This is returned as a tuple, eg. ((xPos,yPos),(width,height))
    '''
    # The standard form of the cartridge offset is image pixels, this converts to steps.
    cartridgeOffset = (int(round(cartridgeOffset[0] * stepsPerPixel)), \
                       int(round(cartridgeOffset[1] * stepsPerPixel)))

    # Initialize some values for storing the current position and image edges.
    xPos, yPos, xMax, yMax = 0,0,0,0
    xMin, yMin = sys.maxint, sys.maxint

    # For each command that has been parsed
    for cmd in cmds:
        # If the command is to move the carriage
        if cmd[0] == MOVE_CMD:
            displacement = cmd[1][1]
            if cmd[1][0] == X_AXIS:
                xPos += displacement
            if cmd[1][0] == Y_AXIS:
                yPos += displacement
        if cmd[0] == FIRE_CMD:
            for primitive in range(cartridge.numPrimitives):
                if cmd[1][1] & (1 << primitive) or cmd[1][2] & (1 << primitive):
                    offset = cartridge.nozzleDisplacement(cmd[1][0], primitive)
                    offset = (int(round(offset[0]*stepsPerPixel)),int(round(offset[1]*\
                                                                     stepsPerPixel)))
##                    print "----"
##                    print xPos, cmd, offset
##                    print xMin, yMin, xMax, yMax
                    if cmd[1][1] & (1 << primitive):
                        xMin = min(xPos+offset[0], xMin)
                        xMax = max(xPos+offset[0], xMax)
                        yMin = min(yPos+offset[1], yMin)
                        yMax = max(yPos+offset[1], yMax)
                    if cmd[1][2] & (1 << primitive):
                        offset = (offset[0]+cartridgeOffset[0],offset[1]+cartridgeOffset[1])
                        xMin = min(xPos+offset[0], xMin)
                        xMax = max(xPos+offset[0], xMax)
                        yMin = min(yPos+offset[1], yMin)
                        yMax = max(yPos+offset[1], yMax)
    
    width = (xMax - xMin) + 3
    height = (yMax - yMin) + 6
    
    xMin *= -1
    xMin += 2
    
    yMin *= -1
    yMin += 2
    
    if xMin == sys.maxint or yMin == sys.maxint:
        return ((0,0), (-1,-1))
    return ((xMin, yMin), (width, height))

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


def decodeCmd(cmdStr):
    cmdByte = cmdStr[0]

    if cmdByte == 'M':
        cmdType = MOVE_CMD
        data = decodeMoveData(cmdStr[2:])
    elif cmdByte == 'F':
        cmdType = FIRE_CMD
        data = decodeFireData(cmdStr[2:])
    elif cmdByte == 'S':
        cmdType = SIZE_CMD
        data = decodeSizeData(cmdStr[2:])

    return (cmdType, data)

def decodeSizeData(dataStr):
    width = int(dataStr.split(' ')[0])
    height = int(dataStr.split(' ')[1])
    return (width,height)

def decodeFireData(dataStr):
    address = mirrorNibble(int(dataStr[0:1], 16)) - 1
    firingLeft = int(dataStr[1:3], 16)
    firingRight = int(dataStr[3:5], 16)
    return (address, firingLeft, firingRight)

def decodeMoveData(dataStr):
    if dataStr[0] == 'X':
        axis = X_AXIS
    else:
        axis = Y_AXIS

    displacement = int(dataStr[2:])
    return (axis, displacement)




def imageFromCmds(cmds, cartridge, cartridgeOffset, stepsPerPixel):

    if (cmds[0][0] == SIZE_CMD):
        actualImageWidth,actualImageHeight = cmds[0][1]
    else:
    
        stepWidth = 0
        i = 0
        while cmds[i][0] != FIRE_CMD:
            i += 1
        
        while (cmds[i][0] != MOVE_CMD) or (cmds[i][1][0] != Y_AXIS):
            i +=1
        
        feedAdvance = int(round(cmds[i][1][1] / stepsPerPixel))
        
        i += 1
        while (cmds[i][0] != MOVE_CMD) or (cmds[i][1][0] != Y_AXIS):
            i +=1
            if (cmds[i][0] == MOVE_CMD) and (cmds[i][1][0] == X_AXIS):
                if cmds[i][1][1] > 0:
                    stepWidth += cmds[i][1][1]
        pixelWidth = int(round(stepWidth / stepsPerPixel))
        actualImageWidth = pixelWidth - (cartridge.columnOffset + cartridgeOffset[0])
        
        pixelHeight = abs(int(round(cmds[-1][1][1]) / stepsPerPixel))
        actualImageHeight = pixelHeight - cartridge.swathHeight + (2*feedAdvance)\
                                           - abs(cartridgeOffset[1])

    #actualImageWidth = 1200
    #actualImageHeight = 500
    print actualImageWidth, actualImageHeight
    outputImage = Image.new("RGBA", (actualImageWidth, actualImageHeight), (255,255,255,0))
    imageData = outputImage.load()
    
    xPos = 0
    yPos = 0
    cmdCnt = -1
    swathImages = []
    
    for cmd in cmds:
        cmdCnt += 1
        if cmd[0] == FIRE_CMD:
            for primitive in range(8):
                if cmd[1][1] & (1 << primitive):
                    offset = cartridge.nozzleDisplacement(cmd[1][0], primitive)
                    pos = (xPos + offset[0], yPos + offset[1])
                    try:
                        imageData[pos[0],pos[1]] = (0,imageData[pos[0],pos[1]][1],\
                                                    imageData[pos[0],pos[1]][2],\
                                                    imageData[pos[0],pos[1]][3] + 1)
                        #print "OK pos"
                        #print pos
                    except:
                        print "pos"
                        print pos
                if cmd[1][2] & (1 << primitive):
                    offset = cartridge.nozzleDisplacement(cmd[1][0], primitive)
                    pos = (xPos + offset[0] + cartridgeOffset[0], yPos + offset[1])
                    try:
                        imageData[pos[0],pos[1]] = (imageData[pos[0],pos[1]][0],0,\
                                                imageData[pos[0],pos[1]][2],\
                                                imageData[pos[0],pos[1]][3] + 1)
                        #print "OK pos"
                        #print pos
                    except:
                        print "pos"
                        print pos
                        
        elif cmd[0] == MOVE_CMD:
            displacement = int(round(cmd[1][1] / stepsPerPixel))
            if cmd[1][0] == X_AXIS:
                xPos += displacement
            elif cmd[1][0] == Y_AXIS:
                newSwath = outputImage.copy()
                newSwathData = newSwath.load()
                if yPos > 2 and (yPos - 2) < (actualImageHeight):
                    for x in range(actualImageWidth):
                        newSwathData[x, yPos-2] = (0,0,0,255)
                        if x % 2 == 0:
                            newSwathData[x, yPos-1] = (0,0,0,255)
                if (yPos+cartridge.swathHeight) < (actualImageHeight - 2):
                    for x in range(actualImageWidth):
                        newSwathData[x, yPos+cartridge.swathHeight+2] = (0,0,0,255)
                        if x % 2 == 0:
                            newSwathData[x, yPos+cartridge.swathHeight+1] = (0,0,0,255)                            
                swathImages.append(newSwath)
                complete = cmdCnt
                total = len(cmds)
                percentage = int(float(complete) / total * 100)
                print "{:d}% Image Simulation Complete".format(percentage)
                yPos += displacement

    maxVal = 0
    for x in range(actualImageWidth):
        for y in range(actualImageHeight):
            if imageData[x,y][3] > maxVal:
                maxVal = imageData[x,y][3]
    
    for x in range(actualImageWidth):
        for y in range(actualImageHeight):
            imageData[x,y] = (imageData[x,y][0],imageData[x,y][1],imageData[x,y][2],\
                              int((float(imageData[x,y][3]) / maxVal) * 255))

    for i in range(len(swathImages)):
        data = swathImages[i].load()
        for x in range(actualImageWidth):
            for y in range(actualImageHeight):
                data[x,y] = (data[x,y][0],data[x,y][1],data[x,y][2],\
                              int((float(data[x,y][3]) / maxVal) * 255))
    #outputImage.show()
    
    #return swathImages
    return [outputImage]

def addWODup(item, array):
    duplicate = False
    for item2 in array:
        if item == item2:
            duplicate = True
            break
    if not (duplicate):
        array.append(item)

def mirrorMirror(inputCoords):
    output = []
    for item in inputCoords:
        addWODup(item, output)
        if item[0] != 0:
            addWODup((-item[0],item[1]), output)
        if item[1] != 0:
            addWODup((item[0],-item[1]), output)
        if item[0] != 0 and item[1] != 0:
            addWODup((-item[0],-item[1]), output)
        if item[0] != item[1]:
            addWODup((item[1],item[0]), output)
    return tuple(output)

def circleVal(x, radius):
    return sqrt(radius**2 - x**2)

def getCirclePixels(radius):
    radius -= 0.5
    output = []
    for x in range(int(radius+1)):
        for y in range(int(radius+1)):
            if y <= circleVal(x,radius):
                output.append((x,y))
    return mirrorMirror(tuple(output))
        

def dot(imageData, pos, size, isLeftSide, offsets, showAscorbic=True):
    
    for offset in offsets:
        newPos = (pos[0]+offset[0], pos[1]+offset[1])
        if (newPos[0] < size[0]) and (newPos[0] >= 0) and (newPos[1] < size[1]) and \
           (newPos[1] >= 0):
            if isLeftSide:
                imageData[newPos[0],newPos[1]] = (0,imageData[newPos[0],newPos[1]][1],\
                                            imageData[newPos[0],newPos[1]][2],\
                                            imageData[newPos[0],newPos[1]][3] + 1)
            elif (showAscorbic):
                imageData[newPos[0],newPos[1]] = (imageData[newPos[0],pos[1]][0],0,\
                                            imageData[newPos[0],newPos[1]][2],\
                                            imageData[newPos[0],newPos[1]][3] + 1)
    

def imageFromCmds2(cmds, cartridge, cartridgeOffset, stepsPerPixel, offsets, \
                   showAscorbic=True):

    (xPos, yPos), (width, height) = determineSize(cmds, cartridge, cartridgeOffset, \
                                                  stepsPerPixel)
    #height += int(round(cartridge.swathHeight*stepsPerPixel))
    cartridgeOffset = (int(round(cartridgeOffset[0] * stepsPerPixel)), \
                       int(round(cartridgeOffset[1] * stepsPerPixel)))
    print "WIDTH, HEIGHT"
    print width,height
    print "xPos, yPos"
    print xPos, yPos
    
    #outputImage = Image.new("RGBA", (width, height), (255,255,255,0))
    outputImage = Image.new("RGBA", (width, height), (255,255,255,1))
    imageData = outputImage.load()
    
    #xPos = 0
    #yPos = 0
    cmdCnt = -1
    swathImages = []
    
    for cmd in cmds:
        cmdCnt += 1
        if cmd[0] == FIRE_CMD:
            for primitive in range(8):
                if cmd[1][1] & (1 << primitive) or cmd[1][2] & (1 << primitive):
                    offset = cartridge.nozzleDisplacement(cmd[1][0], primitive)
                    offset = (int(round(offset[0]*stepsPerPixel)), \
                              int(round(offset[1]*stepsPerPixel)))
                    if cmd[1][1] & (1 << primitive):
                        pos = (xPos + offset[0], yPos + offset[1])
                        dot(imageData, pos, (width,height), cmd[1][1] & (1 << primitive),\
                            offsets, showAscorbic)
                    if cmd[1][2] & (1 << primitive):
                        pos = (xPos + offset[0] + cartridgeOffset[0], yPos + offset[1])
                        dot(imageData, pos, (width,height), cmd[1][1] & (1 << primitive),\
                            offsets, showAscorbic)
                        
        elif cmd[0] == MOVE_CMD:
            displacement = cmd[1][1]
            if cmd[1][0] == X_AXIS:
                xPos += displacement
            elif cmd[1][0] == Y_AXIS:
                newSwath = outputImage.copy()
                newSwathData = newSwath.load()
                swathHeightSteps = int(round(cartridge.swathHeight*stepsPerPixel))
                if yPos > 2 and (yPos - 2) < (height):
                    for x in range(width):
                        newSwathData[x, yPos-2] = (0,0,0,255)
                        if x % 2 == 0:
                            newSwathData[x, yPos-1] = (0,0,0,255)
                if (yPos+swathHeightSteps) < (height - 2):
                    for x in range(width):
                        newSwathData[x, yPos+swathHeightSteps+2] = (0,0,0,255)
                        if x % 2 == 0:
                            newSwathData[x, yPos+swathHeightSteps+1] = (0,0,0,255)                            
                swathImages.append(newSwath)
                complete = cmdCnt
                total = len(cmds)
                percentage = int(float(complete) / total * 100)
                print "{:d}% Image Simulation Complete".format(percentage)
                yPos += displacement

    
    print "starting Equalization"
    maxVal = 0
    for x in range(width):
        for y in range(height):
            if imageData[x,y][3] > maxVal:
                maxVal = imageData[x,y][3]
    
    for x in range(width):
        for y in range(height):
            imageData[x,y] = (imageData[x,y][0],imageData[x,y][1],imageData[x,y][2],\
                              int((float(imageData[x,y][3]) / maxVal) * 255))

    print "Equalized main image"
    
    
    print "Equalizing each swath image"
    
    for i in range(len(swathImages)):
        data = swathImages[i].load()
        for x in range(width):
            for y in range(height):
                data[x,y] = (data[x,y][0],data[x,y][1],data[x,y][2],\
                              int((float(data[x,y][3]) / maxVal) * 255))

    print "Equalized all images"
    
    outputImage.show()
    
    return swathImages
    #return [outputImage]

def simulateGUI(inputFile, showAscorbic=True, offsets=None):
    global root
    global images

    if not(offsets):
        offsets = getCirclePixels(4)
    inputFile = open(inputFile)
    lines = inputFile.readlines()
    inputFile.close()

    cmds = [decodeCmd(cmdStr) for cmdStr in lines]

    images = imageFromCmds2(cmds, HP40Cartridge(), (726,0),(25.4/600/0.0125), offsets,\
                            showAscorbic)
    maxIndex = len(images)-1

    root = Tk()
    root.index = 0
    root.zoom = 1.0
    root.maxIndex = len(images)-1
    root.img = PhotoImage(images[root.index])

    scrollbarY = Scrollbar(root, orient=VERTICAL)
    scrollbarY.grid(row=0, column=2, sticky="NS")
    scrollbarX = Scrollbar(root, orient=HORIZONTAL)
    scrollbarX.grid(row=1, column=0, columnspan=2, sticky="EW")

    root.canvasSize = (1000,600)
    root.canvas = Canvas(root, yscrollcommand=scrollbarY.set, xscrollcommand=scrollbarX.set,\
                         width=root.canvasSize[0], height=root.canvasSize[1])
    width, height = images[root.index].size
    root.canvas.grid(row=0, column=0, columnspan=2)
    scrollbarY.config(command=root.canvas.yview)
    scrollbarX.config(command=root.canvas.xview)
    imageX = int((root.canvasSize[0] / 2) - (width / 2))
    imageY = int((root.canvasSize[1] / 2) - (height / 2))
    root.canvas.create_image(imageX,imageY,image=root.img, anchor="nw")
    root.canvas.config(scrollregion=root.canvas.bbox(ALL))
    # scrollbarY.focus_set()


    forwardBtn = Button(root, text="Next", command=nextImage)
    prevBtn = Button(root, text="Previous", command=prevImage)
    forwardBtn.grid(row=2,column=1)
    prevBtn.grid(row=2,column=0)

    zoomInBtn = Button(root, text="Zoom In", command=zoomIn)
    zoomOutBtn = Button(root, text="Zoom Out", command=zoomOut)
    zoomInBtn.grid(row=3,column=1)
    zoomOutBtn.grid(row=3,column=0)

    #img = PhotoImage(images[0])
    #lbl = Label(frame, image=img)
    #lbl.pack()


    #root.geometry('{}x{}'.format(500, 500))
    root.mainloop()

root = []
images = []


if __name__ == "__main__":
    #simulateGUI("testCommands.hex", showAscorbic=False, offsets = getCirclePixels(6))
    simulateGUI("textTest.hex", showAscorbic=False, offsets = getCirclePixels(6))













