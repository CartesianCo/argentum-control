#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control GUI

author: Michael Shiel
author: Trent Waddington
"""

import sys
import os
import time
from PyQt4 import QtGui, QtCore

from serial.tools.list_ports import comports
from ArgentumPrinterController import ArgentumPrinterController
from PrintView import PrintView
from avrdude import avrdude

import pickle

from imageproc import ImageProcessor

from Alchemist import OptionsDialog, CommandLineEdit, ServoCalibrationDialog

import esky
from setup import VERSION, BASEVERSION
from firmware_updater import update_firmware_list, get_available_firmware, update_local_firmware, is_older_firmware

import subprocess
from multiprocessing import Process
import threading

NO_PRINTER = "No printer connected."

def myrun(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = []
    while True:
        line = p.stdout.readline()
        stdout.append(line)
        print(line)
        if line == '' and p.poll() != None:
            break
    return ''.join(stdout)

default_options = {
    'horizontal_offset': 726,
    'vertical_offset': 0,
    'print_overlap': 41
}

def load_options():
    try:
        options_file = open('argentum.pickle', 'rb')

    except:
        print('No existing options file, using defaults.')

        return default_options

    return pickle.load(options_file)

def save_options(options):
    try:
        options_file = open('argentum.pickle', 'wb')
    except:
        print('Unable to open options file for writing.')

    pickle.dump(options, options_file)

class Argentum(QtGui.QMainWindow):
    def __init__(self):
        super(Argentum, self).__init__()

        #v = Process(target=updater, args=('http://files.cartesianco.com',))
        #v.start()

        self.printer = ArgentumPrinterController()
        self.programmer = None

        self.printing = False
        self.paused = False
        self.autoConnect = True
        self.sentVolt = False

        self.XStepSize = 150
        self.YStepSize = 200

        self.options = load_options()
        try:
            self.lastRun = int(self.options['last_run'])
        except:
            self.lastRun = None
        self.options['last_run'] = int(time.time())
        save_options(self.options)

        #print('Loaded options: {}'.format(self.options))

        self.initUI()

        self.appendOutput('Argentum Control, Version {}'.format(VERSION))

        if hasattr(sys, "frozen"):
            try:
                app = esky.Esky(sys.executable, 'http://files.cartesianco.com')

                new_version = app.find_update()

                if new_version:
                    self.appendOutput('Update available! Select update from the Utilities menu to upgrade. [{} -> {}]'
                        .format(app.active_version, new_version))

                    self.statusBar().showMessage('Update available!')

            except Exception as e:
                self.appendOutput('Update exception.')
                self.appendOutput(str(e))

                pass
        else:
            #self.appendOutput('Update available! Select update from the Utilities menu to upgrade. [{} -> {}]'
            #    .format('0.0.6', '0.0.7'))
            pass
            #self.appendOutput('Not packaged - no automatic update support.')

        daily = 60*60*24
        if self.lastRun == None or int(time.time()) - self.lastRun > daily:
            updateThread = threading.Thread(target=self.updateFirmwareLoop)
            updateThread.start()

        # Make a directory where we can place processed images
        docsDir = str(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation))
        self.filesDir = os.path.join(docsDir, 'Argentum')
        if not os.path.isdir(self.filesDir):
            os.mkdir(self.filesDir)
        self.lastImportDir = self.filesDir
        self.lastFirmwareDir = os.getcwd()

    def initUI(self):
        # Create the console
        self.console = QtGui.QWidget(self)

        # First Row
        connectionRow = QtGui.QHBoxLayout()

        portLabel = QtGui.QLabel("Ports:")
        self.portListCombo = QtGui.QComboBox(self)
        self.connectButton = QtGui.QPushButton("Connect")

        self.connectButton.clicked.connect(self.connectButtonPushed)

        self.updatePortListTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.updatePortListTimer, QtCore.SIGNAL("timeout()"), self.updatePortList)
        self.updatePortListTimer.start(1000)

        self.updatePosDisplayTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.updatePosDisplayTimer, QtCore.SIGNAL("timeout()"), self.updatePosDisplay)
        self.updatePosDisplayTimer.start(3000)

        self.portListCombo.setSizePolicy(QtGui.QSizePolicy.Expanding,
                         QtGui.QSizePolicy.Fixed)
        self.portListCombo.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)

        connectionRow.addWidget(portLabel)
        connectionRow.addWidget(self.portListCombo)
        connectionRow.addWidget(self.connectButton)

        # Command Row

        commandRow = QtGui.QHBoxLayout()

        commandLabel = QtGui.QLabel("Command:")
        self.commandField = CommandLineEdit(self) #QtGui.QLineEdit(self)
        self.commandSendButton = QtGui.QPushButton("Send")

        self.commandSendButton.clicked.connect(self.sendButtonPushed)
        self.commandField.connect(self.commandField, QtCore.SIGNAL("enterPressed"), self.sendButtonPushed)

        self.commandField.setSizePolicy(QtGui.QSizePolicy.Expanding,
                         QtGui.QSizePolicy.Fixed)

        commandRow.addWidget(commandLabel)
        commandRow.addWidget(self.commandField)
        commandRow.addWidget(self.commandSendButton)

        # Output Text Window
        self.outputView = QtGui.QTextEdit()

        self.outputView.setReadOnly(True)

        self.outputView.setSizePolicy(QtGui.QSizePolicy.Minimum,
                         QtGui.QSizePolicy.Expanding)

        # Position reporting

        self.posOptionsButton = QtGui.QPushButton("^")
        self.posOptionsButton.setMaximumWidth(20)
        self.posLabel = QtGui.QLabel("0.0, 0.0 mm 0, 0 steps")

        self.posListWidget = QtGui.QListWidget()
        self.posListWidget.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.posListWidget.itemActivated.connect(self.posListWidgetItemActivated)
        self.posSaveButton = QtGui.QPushButton("Save")
        self.posSaveButton.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.posSaveButton.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.posSaveButton.clicked.connect(self.posSaveButtonPushed)
        self.posRemoveButton = QtGui.QPushButton("Remove")
        self.posRemoveButton.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.posRemoveButton.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.posRemoveButton.clicked.connect(self.posRemoveButtonPushed)

        try:
            for pos in self.options["saved_positions"]:
                self.posListWidget.addItem(pos)
        except:
            pass

        # Jog Frame

        jogControlsGrid = QtGui.QGridLayout()

        self.upButton = QtGui.QPushButton('^')
        self.downButton = QtGui.QPushButton('v')
        self.leftButton = QtGui.QPushButton('<')
        self.rightButton = QtGui.QPushButton('>')

        self.makeButtonRepeatable(self.upButton)
        self.makeButtonRepeatable(self.downButton)
        self.makeButtonRepeatable(self.leftButton)
        self.makeButtonRepeatable(self.rightButton)

        self.upButton.clicked.connect(self.incrementY)
        self.downButton.clicked.connect(self.decrementY)
        self.leftButton.clicked.connect(self.decrementX)
        self.rightButton.clicked.connect(self.incrementX)

        QtGui.QShortcut(QtGui.QKeySequence("Left"), self, self.shortcutLeft)
        QtGui.QShortcut(QtGui.QKeySequence("Right"), self, self.shortcutRight)
        QtGui.QShortcut(QtGui.QKeySequence("Up"), self, self.shortcutUp)
        QtGui.QShortcut(QtGui.QKeySequence("Down"), self, self.shortcutDown)
        QtGui.QShortcut(QtGui.QKeySequence("Home"), self, self.shortcutHome)
        QtGui.QShortcut(QtGui.QKeySequence("-"), self, self.shortcutMinus)
        QtGui.QShortcut(QtGui.QKeySequence("+"), self, self.shortcutPlus)

        jogControlsGrid.addWidget(self.upButton, 0, 1)
        jogControlsGrid.addWidget(self.leftButton, 1, 0)
        jogControlsGrid.addWidget(self.rightButton, 1, 2)
        jogControlsGrid.addWidget(self.downButton, 2, 1)

        # Position reporting

        posRow = QtGui.QHBoxLayout()
        posRow.addStretch(1)
        posRow.addWidget(self.posOptionsButton)
        posRow.addWidget(self.posLabel)

        # Main Controls

        controlRow = QtGui.QHBoxLayout()

        self.calibrateButton = QtGui.QPushButton('Calibrate')
        self.printButton = QtGui.QPushButton('Print')
        self.stopButton = QtGui.QPushButton('Stop')
        self.homeButton = QtGui.QPushButton('Home')
        self.processImageButton = QtGui.QPushButton('Process Image')

        self.calibrateButton.clicked.connect(self.calibrateButtonPushed)
        self.printButton.clicked.connect(self.printButtonPushed)
        self.stopButton.clicked.connect(self.stopButtonPushed)
        self.homeButton.clicked.connect(self.homeButtonPushed)
        self.processImageButton.clicked.connect(self.processImageButtonPushed)
        self.posOptionsButton.clicked.connect(self.posOptionsButtonPushed)

        controlRow.addWidget(self.calibrateButton)
        controlRow.addWidget(self.printButton)
        controlRow.addWidget(self.stopButton)
        controlRow.addWidget(self.homeButton)
        controlRow.addWidget(self.processImageButton)

        # Main Vertical Layout

        verticalLayout = QtGui.QVBoxLayout()
        verticalLayout.addLayout(connectionRow)
        verticalLayout.addLayout(commandRow)
        verticalLayout.addWidget(self.outputView)
        verticalLayout.addLayout(jogControlsGrid)
        verticalLayout.addLayout(posRow)
        verticalLayout.addLayout(controlRow)
        self.console.setLayout(verticalLayout)

        # Menu Bar Stuff

        self.flashAction = QtGui.QAction('&Flash Arduino', self)
        self.flashAction.triggered.connect(self.flashActionTriggered)
        self.flashAction.setEnabled(False)

        self.optionsAction = QtGui.QAction('Processing &Options', self)
        self.optionsAction.triggered.connect(self.optionsActionTriggered)
        self.optionsAction.setEnabled(False)

        self.servoCalibrationAction = QtGui.QAction('Servo Calibration', self)
        self.servoCalibrationAction.triggered.connect(self.servoCalibrationActionTriggered)
        self.servoCalibrationAction.setEnabled(False)

        self.uploadFileAction = QtGui.QAction('Upload File', self)
        self.uploadFileAction.triggered.connect(self.uploadFileActionTriggered)
        self.uploadFileAction.setEnabled(False)

        #self.updateAction = QtGui.QAction('&Update', self)
        #self.updateAction.triggered.connect(self.updateActionTriggered)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        self.openLayoutAction = QtGui.QAction('&Open Layout', self)
        self.openLayoutAction.triggered.connect(self.fileOpenLayoutTriggered)
        fileMenu.addAction(self.openLayoutAction)
        self.saveLayoutAction = QtGui.QAction('&Save Layout', self)
        self.saveLayoutAction.triggered.connect(self.fileSaveLayoutTriggered)
        fileMenu.addAction(self.saveLayoutAction)
        self.saveLayoutAsAction = QtGui.QAction('S&ave Layout as...', self)
        self.saveLayoutAsAction.triggered.connect(self.fileSaveLayoutAsTriggered)
        fileMenu.addAction(self.saveLayoutAsAction)
        self.closeLayoutAction = QtGui.QAction('&Close Layout', self)
        self.closeLayoutAction.triggered.connect(self.fileCloseLayoutTriggered)
        fileMenu.addAction(self.closeLayoutAction)
        fileMenu.addSeparator()
        self.importImageAction = QtGui.QAction('&Import Image', self)
        self.importImageAction.triggered.connect(self.fileImportImageTriggered)
        fileMenu.addAction(self.importImageAction)
        fileMenu.addSeparator()
        self.printAction = QtGui.QAction('&Print', self)
        self.printAction.setEnabled(False)
        self.printAction.triggered.connect(self.filePrintTriggered)
        fileMenu.addAction(self.printAction)
        fileMenu.addSeparator()
        self.exitAction = QtGui.QAction("E&xit", self)
        self.exitAction.triggered.connect(self.fileExitActionTriggered)
        fileMenu.addAction(self.exitAction)

        utilitiesMenu = menubar.addMenu('Utilities')
        utilitiesMenu.addAction(self.flashAction)
        utilitiesMenu.addAction(self.optionsAction)
        #utilitiesMenu.addAction(self.updateAction)
        #utilitiesMenu.addAction(self.servoCalibrationAction)
        utilitiesMenu.addAction(self.uploadFileAction)

        self.statusBar().showMessage('Looking for printer...')

        self.disableAllButtonsExceptConnect()

        # Create the Print tab
        self.printWidget = QtGui.QWidget(self)
        horizontalLayout = QtGui.QHBoxLayout()
        self.printView = PrintView(self)
        horizontalLayout.addWidget(self.printView)
        self.printWidget.setLayout(horizontalLayout)

        # Main Window Setup
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setTabPosition(QtGui.QTabWidget.South)
        self.tabWidget.addTab(self.printWidget, "Printer")
        self.tabWidget.addTab(self.console, "Console") # always last
        self.setCentralWidget(self.tabWidget)

        QtCore.QTimer.singleShot(100, self.monitor)

        self.setGeometry(300, 300, 1000, 800)
        self.setWindowTitle('Argentum Control')
        self.show()

    def updateFirmwareLoop(self):
        #update_firmware_list()
        #update_local_firmware()
        pass

    def makeButtonRepeatable(self, button):
        button.setAutoRepeat(True)
        button.setAutoRepeatDelay(100)
        button.setAutoRepeatInterval(80)

    def getImageProcessor(self):
        ip = ImageProcessor(
            horizontal_offset=int(self.options['horizontal_offset']),
            vertical_offset=int(self.options['vertical_offset']),
            overlap=int(self.options['print_overlap'])
        )
        return ip

    def processImage(self):
        ip = self.getImageProcessor()
        inputFileName = QtGui.QFileDialog.getOpenFileName(self, 'Select an image to process', self.lastImportDir)

        inputFileName = str(inputFileName)

        if inputFileName:
            self.lastImportDir = os.path.dirname(inputFileName)
            self.appendOutput('Processing Image ' + inputFileName)
            baseName = os.path.basename(inputFileName)
            if baseName.find('.') != -1:
                baseName = baseName[:baseName.find('.')]
            baseName = baseName + '.hex'
            outputFileName = os.path.join(self.filesDir, baseName)
            self.appendOutput('Writing to ' + outputFileName)
            ip.sliceImage(inputFileName, outputFileName, progressFunc=self.progressFunc)

    def progressFunc(self, y, max_y):
        self.appendOutput('{} out of {}.'.format(y, max_y))
        return True

    def appendOutput(self, output):
        if output.find('+Print complete') != -1:
            self.printComplete()
        self.outputView.append(output)
        # Allow the gui to update during long processing
        QtGui.QApplication.processEvents()

    def monitor(self):
        data = self.printer.monitor()
        if data:
            self.appendOutput(data.decode('utf-8', 'ignore'))
        QtCore.QTimer.singleShot(100, self.monitor)

    ### Button Functions ###

    def servoCalibrationActionTriggered(self):
        optionsDialog = ServoCalibrationDialog(self, None)
        optionsDialog.exec_()

    def uploadProgressFunc(self, pos, size):
        if self.uploadProgressCancel:
            return False
        self.uploadProgressPercent = pos * 100.0 / size
        return True

    def uploadLoop(self):
        self.printer.send(self.uploadThread.filename,
                          progressFunc=self.uploadProgressFunc)
        self.uploadProgress.hide()

    def uploadProgressUpdater(self):
        if self.uploadProgress.wasCanceled():
            self.uploadProgressCancel = True
            return
        if self.uploadProgressPercent:
            self.uploadProgress.setValue(self.uploadProgressPercent)
            self.uploadProgressPercent = None
        QtCore.QTimer.singleShot(100, self.uploadProgressUpdater)

    def uploadFileActionTriggered(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Hex file to upload', self.filesDir)
        filename = str(filename)
        if filename:
            self.uploadProgressPercent = None
            self.uploadProgressCancel = False
            self.uploadProgress = QtGui.QProgressDialog(self)
            self.uploadProgress.setWindowTitle("Uploading")
            self.uploadProgress.setLabelText(os.path.basename(filename))
            self.uploadProgress.show()
            QtCore.QTimer.singleShot(100, self.uploadProgressUpdater)

            self.uploadThread = threading.Thread(target=self.uploadLoop)
            self.uploadThread.filename = filename
            self.uploadThread.start()

    def updateActionTriggered(self):
        reply = QtGui.QMessageBox.question(self, 'Message',
            'But are you sure?', QtGui.QMessageBox.Yes |
            QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)

        if reply == QtGui.QMessageBox.Yes:
            self.app.auto_update()
        else:
            self.appendOutput('Crisis Averted!')

    def enableAllButtons(self, enabled=True):
        self.connectButton.setEnabled(enabled)
        self.commandSendButton.setEnabled(enabled)
        self.commandField.setEnabled(enabled)
        self.upButton.setEnabled(enabled)
        self.downButton.setEnabled(enabled)
        self.leftButton.setEnabled(enabled)
        self.rightButton.setEnabled(enabled)
        self.calibrateButton.setEnabled(enabled)
        self.printButton.setEnabled(enabled)
        self.stopButton.setEnabled(enabled)
        self.homeButton.setEnabled(enabled)
        self.processImageButton.setEnabled(enabled)

    def disableAllButtons(self):
        self.enableAllButtons(False)

    def disableAllButtonsExceptConnect(self):
        self.disableAllButtons()
        self.connectButton.setEnabled(True)

    nagged = False
    checkFlashVersion = None
    def nagFirmwareUpgrade(self):
        if self.nagged:
            return
        self.nagged = True
        reply = QtGui.QMessageBox.question(self, 'Firmware upgrade',
            'This printer is running older firmware. To function correctly with this version of the software, it must be upgraded. Do it now?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.Yes)

        if reply == QtGui.QMessageBox.Yes:
            self.checkFlashVersion = BASEVERSION
            _version = BASEVERSION.replace('.', '_')
            filename = "argentum_" + _version + ".hex"
            self.startFlash(filename)
        else:
            self.appendOutput('Continuing with older firmware.')

    def flashActionTriggered(self):
        if self.programmer != None:
            return

        firmwareFileName = QtGui.QFileDialog.getOpenFileName(self, 'Firmware File', self.lastFirmwareDir)
        firmwareFileName = str(firmwareFileName)

        if firmwareFileName:
            self.lastFirmwareDir = os.path.dirname(firmwareFileName)
            self.startFlash(firmwareFileName)

    def startFlash(self, firmwareFileName):
        self.disableAllButtons()
        self.printer.disconnect()

        self.appendOutput('Flashing {} with {}...'.format(self.printer.port, firmwareFileName))

        self.programmer = avrdude(port=self.printer.port)
        if self.programmer.flashFile(firmwareFileName):
            self.flashingProgress = QtGui.QProgressDialog(self)
            self.flashingProgress.setWindowTitle("Flashing")
            self.flashingProgress.show()
            self.pollFlashingTimer = QtCore.QTimer()
            QtCore.QObject.connect(self.pollFlashingTimer, QtCore.SIGNAL("timeout()"), self.pollFlashing)
            self.pollFlashingTimer.start(1000)
        else:
            self.appendOutput("Can't flash for some reason.")
            self.appendOutput("")
            self.printer.connect()
            self.enableAllButtons()

    def pollFlashing(self):
        self.flashingProgress.setValue(self.flashingProgress.value() + 100 / 30)
        if self.programmer.done():
            self.appendOutput('Flashing completed.')
            self.appendOutput("")
            self.flashingProgress.close()
            self.flashingProgress = None
            self.pollFlashingTimer.stop()
            self.pollFlashingTimer = None
            self.programmer = None

            self.printer.connect()
            if self.checkFlashVersion:
                if self.printer.version == None:
                    self.printer.disconnect()
                    self.printer.connect()
                version = self.printer.version
                if version and version.find('+') != -1:
                    version = version[:version.find('+')]
                if self.checkFlashVersion != version:
                    QtGui.QMessageBox.information(self,
                        "Flash error",
                        "Upgrading the firmware has failed. It is recommended that you exit the program and ensure you have installed the necessary drivers for avrdude.")
                self.checkFlashVersion = None
            self.enableAllButtons()

    def optionsActionTriggered(self):
        """options = {
            'stepSizeX': 120,
            'stepSizeY': 120,
            'xAxis':    '',
            'yAxis':    ''
        }"""

        optionsDialog = OptionsDialog(self, options=self.options)
        optionsDialog.exec_()

    def fileOpenLayoutTriggered(self):
        self.printView.openLayout()

    def fileSaveLayoutTriggered(self):
        self.printView.saveLayout()

    def fileSaveLayoutAsTriggered(self):
        self.printView.layout = None
        self.printView.saveLayout()

    def fileCloseLayoutTriggered(self):
        self.printView.closeLayout()

    def fileImportImageTriggered(self):
        inputFileName = str(QtGui.QFileDialog.getOpenFileName(self, 'Select an image to process', self.lastImportDir, "Image Files (*.png *.xpm *.jpg *.svg *.bmp);;All Files (*.*)"))
        if inputFileName:
            self.lastImportDir = os.path.dirname(inputFileName)
            self.printView.addImageFile(inputFileName)

    def filePrintTriggered(self):
        self.printView.startPrint()

    def fileExitActionTriggered(self):
        if self.printView.closeLayout():
            self.close()

    def enableConnectionSpecificControls(self, enabled):
        self.flashAction.setEnabled(enabled)
        self.printAction.setEnabled(enabled)
        self.optionsAction.setEnabled(enabled)
        self.uploadFileAction.setEnabled(enabled)

        self.portListCombo.setEnabled(not enabled)

    def connectButtonPushed(self):
        if self.printer.connected:
            self.printer.disconnect()

            self.connectButton.setText('Connect')

            self.enableConnectionSpecificControls(False)
            self.disableAllButtonsExceptConnect()
            self.statusBar().showMessage('Disconnected from printer.')
        else:
            port = str(self.portListCombo.currentText())

            if port != NO_PRINTER:
                if self.printer.connect(port=port):
                    self.connectButton.setText('Disconnect')

                    self.enableAllButtons()
                    self.enableConnectionSpecificControls(True)
                    self.statusBar().showMessage('Connected.')
                    self.sentVolt = False

                    if self.printer.version != None:
                        for line in self.printer.junkBeforeVersion:
                            self.appendOutput(line)
                        self.appendOutput("Printer is running: " + self.printer.version)

                    options = self.printer.getOptions()
                    if options != None:
                        for key, value in options.items():
                            self.options[key] = value
                        save_options(self.options)

                    self.homePrinter()

                    if (self.printer.version != None and
                            is_older_firmware(self.printer.version)):
                        self.nagFirmwareUpgrade()
                else:
                    QtGui.QMessageBox.information(self, "Cannot connect to printer", self.printer.lastError)
                    self.statusBar().showMessage('Connection error.')
        self.updatePortList()

    def updatePortList(self):
        curPort = str(self.portListCombo.currentText())

        self.portListCombo.clear()

        portList = []
        for port in comports():
            if (port[2].find("2341:0042") != -1 or
                    port[2].find("2341:42") != -1):
                portList.append(port)

        for port in portList:
            self.portListCombo.addItem(port[0])

        if self.portListCombo.count() == 0:
            self.statusBar().showMessage('No printer connected. Connect your printer.')
            self.portListCombo.addItem(NO_PRINTER)
        else:
            if curPort == "" or self.portListCombo.findText(curPort) == -1:
                if self.portListCombo.count() == 1:
                    curPort = self.portListCombo.itemText(0)
                else:
                    self.statusBar().showMessage('Multiple printers connected. Please select one.')
                    self.tabWidget.setCurrentWidget(self.console)

        if curPort != "":
            idx = self.portListCombo.findText(curPort)
            if idx == -1:
                if self.printer.connected:
                    self.connectButtonPushed()
            else:
                self.portListCombo.setCurrentIndex(idx)
                if self.autoConnect and not self.printer.connected:
                    self.autoConnect = False
                    self.connectButtonPushed()
                    if self.printer.connected:
                        self.tabWidget.setCurrentWidget(self.printWidget)

    def processImageButtonPushed(self):
        self.processImage()

    def updatePosDisplay(self, pos=None):
        if pos == None:
            if not self.printer.connected:
                return
            if self.tabWidget.currentWidget() != self.console:
                return
            if self.printer.getTimeSinceLastCommand() < 1:
                return
            pos = self.printer.getPosition()
            if pos == None:
                return
        self.lastPos = pos
        (xmm, ymm, x, y) = pos
        self.posLabel.setText("{}, {} mm {}, {} steps".format(xmm, ymm, x, y))

    def posOptionsButtonPushed(self):
        if self.posSaveButton.isVisible():
            self.hidePosOptions()
        else:
            self.showPosOptions()

    def showPosOptions(self):
            gp1 = self.posOptionsButton.mapToGlobal(self.posOptionsButton.rect().topLeft())
            gp2 = self.posLabel.mapToGlobal(self.posLabel.rect().bottomRight())
            width = gp2.x() - gp1.x();
            height = width
            saveButtonHeight = gp2.y() - gp1.y()
            self.posListWidget.resize(width, height)
            self.posListWidget.move(gp1.x(), gp1.y() - height - saveButtonHeight)
            self.posSaveButton.move(gp1.x(), gp1.y() - saveButtonHeight)
            self.posSaveButton.show()
            if self.posListWidget.count() > 0:
                self.posRemoveButton.move(gp1.x() + self.posSaveButton.rect().width(), gp1.y() - saveButtonHeight)
                self.posRemoveButton.show()
                self.posListWidget.show()
                self.posListWidget.setFocus()

    def hidePosOptions(self):
        self.posListWidget.hide()
        self.posSaveButton.hide()
        self.posRemoveButton.hide()

    def savePosList(self):
        savedPositions = []
        for n in range(0, self.posListWidget.count()):
            item = self.posListWidget.item(n)
            savedPositions.append(str(item.text()))
        self.options["saved_positions"] = savedPositions
        save_options(self.options)

    def posSaveButtonPushed(self):
        self.updatePosDisplay()
        (xmm, ymm, x, y) = self.lastPos
        str = "{}, {} mm {}, {} steps".format(xmm, ymm, x, y)
        for n in range(0, self.posListWidget.count()):
            item = self.posListWidget.item(n)
            self.posListWidget.setItemSelected(item, False)
        match = self.posListWidget.findItems(str, QtCore.Qt.MatchFlags())
        if len(match) > 0:
            for item in match:
                self.posListWidget.setItemSelected(item, True)
        else:
            item = self.posListWidget.addItem(str)
            self.posListWidget.setItemSelected(item, True)
            self.savePosList()

    def posRemoveButtonPushed(self):
        for item in self.posListWidget.selectedItems():
            self.posListWidget.takeItem(self.posListWidget.indexFromItem(item).row())
            self.savePosList()

    def posListWidgetItemActivated(self, item):
        s = str(item.text())
        s = s[s.find('mm ')+3:]
        x = int(s[:s.find(', ')])
        y = int(s[s.find(', ') + 2:s.find(' steps')])
        self.hidePosOptions()
        self.printer.home(wait=True)
        self.printer.move(x, y)

    ### Command Functions ###

    def servocommand(self, cmd):
        self.printer.command('l ' + cmd)

    def calibrateButtonPushed(self):
        self.printer.calibrate()

    def printButtonPushed(self):
        if self.printing:
            if self.paused:
                self.paused = False
                self.printButton.setText('Pause')
                self.sendResumeCommand()
            else:
                self.paused = True
                self.printButton.setText('Resume')
                self.sendPauseCommand()
        else:
            self.printing = True
            self.paused = False
            self.printButton.setText('Pause')
            self.sendPrintCommand()

    def stopButtonPushed(self):
        self.appendOutput('Stop!')
        self.printer.emergencyStop()
        self.printComplete()

    def printComplete(self):
        self.printing = False
        self.printButton.setText('Print')

    def homeLoop(self):
        self.printer.home(wait=True)

    def homePrinter(self):
        homeThread = threading.Thread(target=self.homeLoop)
        homeThread.start()

    def homeButtonPushed(self):
        self.homePrinter()

    def sendButtonPushed(self):
        command = str(self.commandField.text())

        self.commandField.submit_command()

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

    def checkPower(self):
        if self.sentVolt or not self.printer.connected:
            return
        self.sentVolt = True
        if self.printer.volt() < 9:
            QtGui.QMessageBox.information(self, "Printer error", "The power cable is not connected or the power switch is off.")

    def incrementX(self):
        self.sendMovementCommand(self.XStepSize, None)

    def incrementY(self):
        self.sendMovementCommand(None, self.YStepSize)

    def decrementX(self):
        self.sendMovementCommand(-self.XStepSize, None)

    def decrementY(self):
        self.sendMovementCommand(None, -self.YStepSize)

    def shortcutLeft(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        if self.commandField.hasFocus():
            return
        self.decrementX()

    def shortcutRight(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        self.incrementX()

    def shortcutUp(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        if self.commandField.hasFocus():
            self.commandField.event(QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                    QtCore.Qt.Key_Up,
                                                    QtCore.Qt.NoModifier))
            return
        self.incrementY()

    def shortcutDown(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        if self.commandField.hasFocus():
            self.commandField.event(QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                    QtCore.Qt.Key_Down,
                                                    QtCore.Qt.NoModifier))
            return
        self.decrementY()

    def shortcutHome(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        self.homeButtonPushed()

    def shortcutMinus(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        self.printer.command('--')

    def shortcutPlus(self):
        if self.tabWidget.currentWidget() != self.console:
            return
        self.printer.command('++')

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
        self.options = val
        save_options(self.options)
        if self.printer.connected:
            self.printer.updateOptions(self.options)

    def closeEvent(self, evt):
        sys.exit(0)

def main():
    app = QtGui.QApplication(sys.argv)
    app.setOrganizationName("CartesianCo")
    app.setOrganizationDomain("cartesianco.com")
    app.setApplicationName("ArgentumControl")
    app_icon = QtGui.QIcon()
    app_icon.addFile('Icon.ico', QtCore.QSize(16, 16))
    app_icon.addFile('Icon.ico', QtCore.QSize(24, 24))
    app_icon.addFile('Icon.ico', QtCore.QSize(32, 32))
    app_icon.addFile('Icon.ico', QtCore.QSize(48, 48))
    app_icon.addFile('Icon.ico', QtCore.QSize(256, 256))
    app.setWindowIcon(app_icon)
    ex = Argentum()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
