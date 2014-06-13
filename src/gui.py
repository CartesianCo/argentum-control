#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control GUI

author: Michael Shiel
"""

import sys
from PyQt4 import QtGui, QtCore

from serial.tools.list_ports import comports
from ArgentumPrinterController import ArgentumPrinterController
from avrdude import avrdude

import subprocess

from PIL import Image

class Argentum(QtGui.QMainWindow):
    def __init__(self):
        super(Argentum, self).__init__()

        self.printer = ArgentumPrinterController()

        self.paused = False

        self.XStepSize = 150
        self.YStepSize = 200

        self.initUI()

    def initUI(self):
        widget = QtGui.QWidget(self)

        # First Row
        connectionRow = QtGui.QHBoxLayout()

        portLabel = QtGui.QLabel("Ports:")
        self.portListCombo = QtGui.QComboBox(self)
        self.connectButton = QtGui.QPushButton("Connect")

        self.connectButton.clicked.connect(self.sendConButtonPushed)

        portList = comports()

        for port in portList:
            self.portListCombo.addItem(port[0])

        self.portListCombo.setSizePolicy(QtGui.QSizePolicy.Expanding,
                         QtGui.QSizePolicy.Fixed)

        connectionRow.addWidget(portLabel)
        connectionRow.addWidget(self.portListCombo)
        connectionRow.addWidget(self.connectButton)

        # Command Row

        commandRow = QtGui.QHBoxLayout()

        commandLabel = QtGui.QLabel("Command:")
        self.commandField = QtGui.QLineEdit(self)
        commandSendButton = QtGui.QPushButton("Send")

        commandSendButton.clicked.connect(self.sendButtonPushed)

        self.commandField.setSizePolicy(QtGui.QSizePolicy.Expanding,
                         QtGui.QSizePolicy.Fixed)

        commandRow.addWidget(commandLabel)
        commandRow.addWidget(self.commandField)
        commandRow.addWidget(commandSendButton)

        # Output Text Window
        self.outputView = QtGui.QTextEdit()

        self.outputView.setReadOnly(True)

        self.outputView.setSizePolicy(QtGui.QSizePolicy.Minimum,
                         QtGui.QSizePolicy.Expanding)

        # Jog Frame

        jogControlsGrid = QtGui.QGridLayout()

        upButton = QtGui.QPushButton('^')
        downButton = QtGui.QPushButton('V')
        leftButton = QtGui.QPushButton('<')
        rightButton = QtGui.QPushButton('>')

        self.makeButtonRepeatable(upButton)
        self.makeButtonRepeatable(downButton)
        self.makeButtonRepeatable(leftButton)
        self.makeButtonRepeatable(rightButton)

        upButton.clicked.connect(self.incrementX)
        downButton.clicked.connect(self.decrementX)
        leftButton.clicked.connect(self.decrementY)
        rightButton.clicked.connect(self.incrementY)

        jogControlsGrid.addWidget(upButton, 0, 1)
        jogControlsGrid.addWidget(leftButton, 1, 0)
        jogControlsGrid.addWidget(rightButton, 1, 2)
        jogControlsGrid.addWidget(downButton, 2, 1)

        # Main Controls

        controlRow = QtGui.QHBoxLayout()

        printButton = QtGui.QPushButton('Print')
        self.pauseButton = QtGui.QPushButton('Pause')
        stopButton = QtGui.QPushButton('Stop')
        homeButton = QtGui.QPushButton('Home')
        processFileButton = QtGui.QPushButton('Process File')

        printButton.clicked.connect(self.printButtonPushed)
        self.pauseButton.clicked.connect(self.pauseButtonPushed)
        stopButton.clicked.connect(self.stopButtonPushed)
        homeButton.clicked.connect(self.homeButtonPushed)
        processFileButton.clicked.connect(self.processFileButtonPushed)

        controlRow.addWidget(printButton)
        controlRow.addWidget(self.pauseButton)
        controlRow.addWidget(stopButton)
        controlRow.addWidget(homeButton)
        controlRow.addWidget(processFileButton)

        # Main Vertical Layout

        verticalLayout = QtGui.QVBoxLayout()
        verticalLayout.addLayout(connectionRow)
        verticalLayout.addLayout(commandRow)
        verticalLayout.addWidget(self.outputView)
        verticalLayout.addLayout(jogControlsGrid)
        verticalLayout.addLayout(controlRow)

        #verticalLayout.addStretch(1)

        # Menu Bar Stuff

        self.flashAction = QtGui.QAction('Flash Arduino', self)
        self.flashAction.triggered.connect(self.flashActionTriggered)
        self.flashAction.setEnabled(False)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('Utilities')
        fileMenu.addAction(self.flashAction)

        self.statusBar().showMessage('Ready')


        # Main Window Setup
        widget.setLayout(verticalLayout)
        self.setCentralWidget(widget)

        #for i in xrange(1000):
        #    self.appendOutput("test")

        self.setGeometry(300, 300, 500, 500)
        self.setWindowTitle('Argentum')
        self.show()

    def makeButtonRepeatable(self, button):
        button.setAutoRepeat(True)
        button.setAutoRepeatDelay(100)
        button.setAutoRepeatInterval(80)

    def showDialog(self):

        inputFileName = QtGui.QFileDialog.getOpenFileName(self, 'File to process', '~')

        inputFileName = str(inputFileName)

        if inputFileName:
            inputImage = Image.open(inputFileName)

            outputFileName = QtGui.QFileDialog.getSaveFileName(self, 'Output file', 'Output.hex', '.hex')

            sliceImage(outputFileName, inputImage)

    def appendOutput(self, output):
        self.outputView.append(output)

    def monitor(self):
        #if self.printer.connected and self.printer.serialDevice.inWaiting():
        #    self.appendOutput(self.printer.serialDevice.readline())

        #self.after(100, self.monitor)
        QtCore.QTimer.singleShot(100, self.monitor)

    ### Button Functions ###

    def flashActionTriggered(self):
        firmwareFileName = QtGui.QFileDialog.getOpenFileName(self, 'Firmware File', '~')
        firmwareFileName = str(firmwareFileName)

        if firmwareFileName:
            self.printer.disconnect()

            programmer = avrdude(port=self.printer.port)
            programmer.flashFile(firmwareFileName)

            self.printer.connect()

    def enableConnectionSpecificControls(self, enabled):
        self.flashAction.setEnabled(enabled)

        QtCore.QTimer.singleShot(100, self.monitor)

    def sendConButtonPushed(self):
        if(self.printer.connected):
            self.printer.disconnect()

            self.connectButton.setText('Connect')
            self.portListCombo.setEnabled(True)

            self.enableConnectionSpecificControls(False)
        else:
            port = str(self.portListCombo.currentText())

            if self.printer.connect(port=port):
                self.connectButton.setText('Disconnect')
                self.portListCombo.setEnabled(False)

                self.enableConnectionSpecificControls(True)

                self.appendOutput('Opened port [{}]'.format(port))

    def processFileButtonPushed(self):
        self.appendOutput('Process File')

        self.showDialog()

    ### Command Functions ###

    def sendCommand(self, command):
        # Remove the last character (new line)
        self.appendOutput(command[:-1])

    def printButtonPushed(self):
        self.sendPrintCommand()

    def pauseButtonPushed(self):
        if(self.paused):
            self.paused = False
            self.pauseButton.setText('Pause')
            self.sendResumeCommand()
        else:
            self.paused = True
            self.pauseButton.setText('Resume')
            self.sendPauseCommand()

    def stopButtonPushed(self):
        self.sendStopCommand()

    def homeButtonPushed(self):
        self.printer.move(0, 0)

    def sendButtonPushed(self):
        command = self.commandField.text() + '\n'
        self.printer.command(command)

    def sendPrintCommand(self):
        self.printer.start()

    def sendPauseCommand(self):
        self.printer.pause()

    def sendResumeCommand(self):
        self.printer.resume()

    def sendStopCommand(self):
        self.printer.stop()

    def sendMovementCommand(self, x, y):
        self.printer.move(x, y)

    def incrementX(self):
        self.sendMovementCommand(self.XStepSize, None)

    def incrementY(self):
        self.sendMovementCommand(None, self.YStepSize)

    def decrementX(self):
        self.sendMovementCommand(-self.XStepSize, None)

    def decrementY(self):
        self.sendMovementCommand(None, -self.YStepSize)

    # This function is for future movement functionality (continuous movement)
    def handleClicked(self):
        if self.isDown():
            if self._state == 0:
                self._state = 1
                self.setAutoRepeatInterval(50)
                print 'press'
            else:
                print 'repeat'
        elif self._state == 1:
            self._state = 0
            self.setAutoRepeatInterval(1000)
            print 'release'
        else:
            print 'click'


### Image Processing Functions

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

def sliceImage(fileThing, inputImage):
    #directory = direct
    # Global variables to hold the images we are working with
    global outputImages
    global pixelMatrices

    outputImages = []
    pixelMatrices = []

    fileThing = open(fileThing, 'wb')

    # Go to our working directory and open/create the output file
    #os.chdir(directory)
    hexOutput = fileThing

    # Open our image and split it into its odd rows and even rows
    #inputImage = Image.open(imageFile)
    inputs = splitImageTwos(inputImage)

    # Get the size of the input images and adjust width to be that of the output
    width, height = inputs[0].size
    width += HEADOFFSET + PRIMITIVEOFFSET

    # Adjust the height. First make sure it is divisible by 25. Then add an
    # extra 2 rows of blank lines.
    height += (mOffset - height%mOffset)
    height += (int(208/mOffset) * mOffset)
    #height += (104*2)

    # Create the output images and put them into a tuple for easy referencing
    outputImages = [Image.new('RGBA', (width,height), (255,255,255,255)) for i in range(4)]

    # Paste the split input image into correct locations on output images
    pasteLocations = ((HEADOFFSET, (int(208/mOffset) * mOffset)/2), (HEADOFFSET+PRIMITIVEOFFSET, (int(208/mOffset) * mOffset)/2), (0, (int(208/mOffset) * mOffset)/2 + VOFFSET), (PRIMITIVEOFFSET, (int(208/mOffset) * mOffset)/2 + VOFFSET))
    for i in range(4):
        outputImages[i].paste(inputs[i%2], pasteLocations[i])
        #outputImages[i].show()

    #pixelMatrices = (outputImages[0][0].load(), outputImages[0][1].load(),
    #outputImages[0][2].load(), outputImages[0][3].load())
    pixelMatrices = [outputImages[i].load() for i in range(4)]

    # We have our input images and their matrices. Now we need to generate the
    # correct output data.
    writeCommands(hexOutput)

    # Construct image from Output.hex
    #simulateImage()



def writeCommands(outputStream):

    width, height = outputImages[0].size
    height -= (int(208/mOffset) * mOffset) # Ignore empty pixels added to the bottom of the file.
    print height
    # Move right 400 steps
    #outputStream.write('M X 3000\n')

    yposition = 0

    for y in range(height/mOffset*2 + 1):

        # Print out progress
        print '{} out of {}.'.format(y + 1, height/mOffset*2 + 1)

        move = 0
        xposition = 0

        # Iterate through the width of the image(s)
        for x in range(width):

            firings = [[calculateFiring(x, y, a, 0), calculateFiring(x, y, a, 1)] for a in range(13)]

            if not any([any(firings[i]) for i in range(len(firings))]):
                #move += (int((x + 1) * SPN) - xposition - move)
                move = (int((x + 1) * SPN) - xposition)
                continue
            elif move != 0 :
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

                        address = ((a + 1) & 0b00000001) << 3
                        address += ((a + 1) & 0b00000010) << 1
                        address += ((a + 1) & 0b00000100) >> 1
                        address += ((a + 1) & 0b00001000) >> 3

                        if 1 == 1:
                            outputStream.write(chr(1)) # Fire command
                            outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                            outputStream.write(chr(address)) # The address we are firing on
                            outputStream.write(chr(0))

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

    firing = 0

    x = xPos
    y = (yPos * mOffset)/2 + (positions[0][addr] * 2)
    if yPos % 2: y += 1
    for i in range(4):
        if pixelMatrices[side*2][x, y][2] <= 200:
            firing += 1 << (i*2)
        y += 26

    y = (yPos * mOffset)/2 + (positions[1][addr] * 2)
    if yPos % 2: y += 1
    for i in range(4):
        if pixelMatrices[side*2 + 1][x, y][2] <= 200:
            firing += 1 << (i*2 + 1)
        y += 26

    return firing

'''
Splits an input image into two images.
'''
def splitImageTwos(image):
    width, height = image.size

    if height % 4 != 0:
        height += (4 - (height % 4))

    odd = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))
    even = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))

    evenMatrix = even.load()
    oddMatrix = odd.load()
    inputMatrix = image.load()

    for y in range((height / 4) - 1):
        for x in range(width):
            oddMatrix[x, y*2] = inputMatrix[x, y*4]
            oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]
            evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
            evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

    y = (height / 4) - 1
    for x in range(width):
        if y*4 < image.size[1]: oddMatrix[x, y*2] = inputMatrix[x, y*4]
        if y*4 + 1 < image.size[1]: oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]
        if y*4 + 2 < image.size[1]: evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
        if y*4 + 3 < image.size[1]: evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

    return (odd, even)

class InputDialog(QtGui.QDialog):
   '''
   this is for when you need to get some user input text
   '''
   def __init__(self, parent=None, title='user input', label='comment', text=''):

       QtGui.QWidget.__init__(self, parent)

       #--Layout Stuff---------------------------#
       mainLayout = QtGui.QVBoxLayout()

       layout = QtGui.QHBoxLayout()
       self.label = QtGui.QLabel()
       self.label.setText(label)
       layout.addWidget(self.label)

       self.text = QtGui.QLineEdit(text)
       layout.addWidget(self.text)

       mainLayout.addLayout(layout)

       #--The Button------------------------------#
       layout = QtGui.QHBoxLayout()
       button = QtGui.QPushButton("okay") #string or icon
       #self.connect(button, QtCore.SIGNAL("clicked()"), self.close)
       button.clicked.connect(self.close)
       layout.addWidget(button)

       mainLayout.addLayout(layout)
       self.setLayout(mainLayout)

       self.resize(400, 60)
       self.setWindowTitle(title)

def main():

    app = QtGui.QApplication(sys.argv)
    ex = Argentum()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
