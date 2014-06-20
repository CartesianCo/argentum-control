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

from imageproc import ImageProcessor

from Alchemist import OptionsDialog

import esky

class Argentum(QtGui.QMainWindow):
    def __init__(self):
        super(Argentum, self).__init__()

        self.printer = ArgentumPrinterController()

        self.paused = False

        self.XStepSize = 150
        self.YStepSize = 200

        self.initUI()

        if hasattr(sys, "frozen"):
            try:
                self.app = esky.Esky(sys.executable, "http://update.shiel.io")

                new_version = self.app.find_update()

                if new_version:
                    self.appendOutput('Update available! Select update from the Utilities menu to upgrade. [{} -> {}]'
                        .format(self.app.active_version, self.app.find_update()))

                     self.statusBar().showMessage('Update available!')

            except Exception, e:
                self.appendOutput('Update exception.')
                self.appendOutput(str(e))
                pass

    def initUI(self):
        widget = QtGui.QWidget(self)

        # First Row
        connectionRow = QtGui.QHBoxLayout()

        portLabel = QtGui.QLabel("Ports:")
        self.portListCombo = QtGui.QComboBox(self)
        self.connectButton = QtGui.QPushButton("Connect")

        self.connectButton.clicked.connect(self.connectButtonPushed)

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

        self.flashAction = QtGui.QAction('&Flash Arduino', self)
        self.flashAction.triggered.connect(self.flashActionTriggered)
        self.flashAction.setEnabled(False)

        self.optionsAction = QtGui.QAction('Printer &Options', self)
        self.optionsAction.triggered.connect(self.optionsActionTriggered)
        #self.optionsAction.setEnabled(False)

        self.updateAction = QtGui.QAction('&Update', self)
        self.updateAction.triggered.connect(self.updateActionTriggered)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('Utilities')
        fileMenu.addAction(self.flashAction)
        fileMenu.addAction(self.optionsAction)
        fileMenu.addAction(self.updateAction)

        self.statusBar().showMessage('Ready')

        # Main Window Setup
        widget.setLayout(verticalLayout)
        self.setCentralWidget(widget)

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
            outputFileName = QtGui.QFileDialog.getSaveFileName(self, 'Output file', 'Output.hex', '.hex')

            ip = ImageProcessor()
            ip.sliceImage(inputFileName, outputFileName)

    def appendOutput(self, output):
        self.outputView.append(output)

    def monitor(self):
        if self.printer.connected and self.printer.serialDevice.inWaiting():
            self.appendOutput(self.printer.serialDevice.readline())

        #self.after(100, self.monitor)
        QtCore.QTimer.singleShot(100, self.monitor)

    ### Button Functions ###

    def updateActionTriggered(self):
        reply = QtGui.QMessageBox.question(self, 'Message',
            'But are you sure?', QtGui.QMessageBox.Yes |
            QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)

        if reply == QtGui.QMessageBox.Yes:
            self.app.auto_update()
        else:
            self.appendOutput('Crisis Averted!')

    def flashActionTriggered(self):
        firmwareFileName = QtGui.QFileDialog.getOpenFileName(self, 'Firmware File', '~')
        firmwareFileName = str(firmwareFileName)

        if firmwareFileName:
            self.printer.disconnect()

            programmer = avrdude(port=self.printer.port)
            programmer.flashFile(firmwareFileName)

            self.printer.connect()

    def optionsActionTriggered(self):
        options = {
            'stepSizeX': 120,
            'stepSizeY': 120,
            'xAxis':    '',
            'yAxis':    ''
        }

        optionsDialog = OptionsDialog(self, options=options)
        optionsDialog.exec_()

    def enableConnectionSpecificControls(self, enabled):
        self.flashAction.setEnabled(enabled)
        #self.optionsAction.setEnabled(enabled)

        self.portListCombo.setEnabled(not enabled)

        QtCore.QTimer.singleShot(100, self.monitor)

    def connectButtonPushed(self):
        if(self.printer.connected):
            self.printer.disconnect()

            self.connectButton.setText('Connect')

            self.enableConnectionSpecificControls(False)
        else:
            port = str(self.portListCombo.currentText())

            if self.printer.connect(port=port):
                self.connectButton.setText('Disconnect')

                self.enableConnectionSpecificControls(True)

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
        print command
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
                print('press')
            else:
                print('repeat')
        elif self._state == 1:
            self._state = 0
            self.setAutoRepeatInterval(1000)
            #print 'release'
        #else:
            #print 'click'

    def updateOptions(self, val):
        print(val)

def main():
    app = QtGui.QApplication(sys.argv)
    ex = Argentum()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
