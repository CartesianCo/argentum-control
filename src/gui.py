#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control GUI

author: Michael Shiel
author: Trent Waddington
"""

import sys
import os
import stat
import time
#import webbrowser
import zipfile
import tempfile
import shutil
from PyQt4 import QtGui, QtCore

from serial.tools.list_ports import comports
from ArgentumPrinterController import ArgentumPrinterController
from PrintView import PrintView
from avrdude import avrdude
import requests

import pickle

from imageproc import ImageProcessor

from Alchemist import OptionsDialog, CommandLineEdit, RollerCalibrationDialog

from setup import VERSION, BASEVERSION, CA_CERTS
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

class GetPrinterNumberDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.parent = parent

        self.setWindowTitle("Unknown Printer")
        mainLayout = QtGui.QVBoxLayout()
        label = QtGui.QLabel("You have connected to a new printer!\n\nPlease enter the number located on the back of your printer.\n\nIt should look something like this:")
        mainLayout.addWidget(label)
        example = QtGui.QLabel("")
        example.setStyleSheet('QLabel { background-color: black }')
        example.setPixmap(QtGui.QPixmap("BackPlate.svg"))
        mainLayout.addWidget(example)
        self.printerNum = QtGui.QLineEdit(self)
        self.printerNum.setText("#")
        mainLayout.addWidget(self.printerNum)

        layout = QtGui.QHBoxLayout()
        layout.addStretch()
        cancelButton = QtGui.QPushButton("Later")
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton)
        self.registerButton = QtGui.QPushButton("Register Printer")
        self.registerButton.clicked.connect(self.register)
        layout.addWidget(self.registerButton)
        mainLayout.addLayout(layout)

        self.registerButton.setDefault(True)

        self.setLayout(mainLayout)

    def register(self):
        self.printerNumText = str(self.printerNum.text())
        if len(self.printerNumText) <= 1:
            return
        if self.printerNumText[0] != '#':
            self.printerNumText = '#' + self.printerNumText

        self.parent.setPrinterNumber(self.printerNumText)
        self.accept()

class Argentum(QtGui.QMainWindow):
    def __init__(self):
        super(Argentum, self).__init__()

        print("Argentum init")

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

        self.lastPos = None
        self.latestVersion = None
        self.inlineUpdateUrl = None

        self.options = load_options()

        #print('Loaded options: {}'.format(self.options))

        self.initUI()

        self.appendOutput('Argentum Control, Version {}'.format(VERSION))
        print("Software version " + VERSION)

        self.startUpdateLoop()

        # Make a directory where we can place processed images
        docsDir = str(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation))
        self.filesDir = os.path.join(docsDir, 'Argentum')
        if not os.path.isdir(self.filesDir):
            os.mkdir(self.filesDir)
        self.lastImportDir = self.filesDir
        self.lastFirmwareDir = os.getcwd()

        self.printStartTime = None

    def initUI(self):
        # Create the console
        self.console = QtGui.QWidget(self)
        self.printView = PrintView(self)

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

        self.flashAction = QtGui.QAction('&Change Firmware', self)
        self.flashAction.triggered.connect(self.flashActionTriggered)
        self.flashAction.setEnabled(False)

        self.optionsAction = QtGui.QAction('Processing &Options', self)
        self.optionsAction.triggered.connect(self.optionsActionTriggered)
        self.optionsAction.setEnabled(False)

        self.rollerCalibrationAction = QtGui.QAction('Roller Calibration', self)
        self.rollerCalibrationAction.triggered.connect(self.rollerCalibrationActionTriggered)
        self.rollerCalibrationAction.setEnabled(False)

        self.uploadFileAction = QtGui.QAction('Upload File', self)
        self.uploadFileAction.triggered.connect(self.uploadFileActionTriggered)
        self.uploadFileAction.setEnabled(False)

        self.printFileAction = QtGui.QAction('&Print File', self)
        self.printFileAction.triggered.connect(self.printFileActionTriggered)
        self.printFileAction.setEnabled(False)

        self.processImageAction = QtGui.QAction('&Process Image', self)
        self.processImageAction.triggered.connect(self.processImageActionTriggered)

        self.updateAction = QtGui.QAction('&Update Software', self)
        self.updateAction.triggered.connect(self.updateActionTriggered)

        self.changePrinterNumAction = QtGui.QAction("&Change Printer Number", self)
        self.changePrinterNumAction.triggered.connect(self.askForPrinterNumber)


        self.showPrintHeadAction = QtGui.QAction('Print &Head', self)
        self.showPrintHeadAction.setCheckable(True)
        self.showPrintHeadAction.triggered.connect(self.printView.showPrintHeadActionTriggered)

        self.showPrintLimsAction = QtGui.QAction('Print &Limits', self)
        self.showPrintLimsAction.setCheckable(True)
        self.showPrintLimsAction.setChecked(True)
        self.showPrintLimsAction.triggered.connect(self.printView.showPrintLimsActionTriggered)

        self.ratePrintAction = QtGui.QAction('&Rate Last Print', self)
        self.ratePrintAction.triggered.connect(self.printView.ratePrintActionTriggered)

        self.dryAction = QtGui.QAction('&Dry', self)
        self.dryAction.triggered.connect(self.printView.dryActionTriggered)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
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

        editMenu = menubar.addMenu('&Edit')
        cutAction = QtGui.QAction('Cu&t', self)
        cutAction.setShortcut(QtGui.QKeySequence("Ctrl+X"))
        cutAction.triggered.connect(self.printView.cut)
        copyAction = QtGui.QAction('&Copy', self)
        copyAction.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        copyAction.triggered.connect(self.printView.copy)
        pasteAction = QtGui.QAction('&Paste', self)
        pasteAction.setShortcut(QtGui.QKeySequence("Ctrl+V"))
        pasteAction.triggered.connect(self.printView.paste)
        deleteAction = QtGui.QAction('&Delete', self)
        deleteAction.setShortcut(QtGui.QKeySequence("Delete"))
        deleteAction.triggered.connect(self.printView.delete)
        editMenu.addAction(cutAction)
        editMenu.addAction(copyAction)
        editMenu.addAction(pasteAction)
        editMenu.addAction(deleteAction)
        editMenu.addSeparator()
        preferencesAction = QtGui.QAction('Preferences', self)
        preferencesAction.triggered.connect(self.preferencesActionTriggered)
        editMenu.addAction(preferencesAction)

        viewMenu = menubar.addMenu('&View')
        viewMenu.addAction(self.showPrintHeadAction)
        viewMenu.addAction(self.showPrintLimsAction)
        viewMenu.addSeparator()
        self.viewSwitchAction = QtGui.QAction("Console", self)
        self.viewSwitchAction.triggered.connect(self.viewSwitchActionTriggered)
        viewMenu.addAction(self.viewSwitchAction)

        printerMenu = menubar.addMenu('Printer')
        self.printerMenu = printerMenu
        printerMenu.addAction(self.optionsAction)
        printerMenu.addAction(self.rollerCalibrationAction)
        printerMenu.addAction(self.changePrinterNumAction)
        printerMenu.addSeparator()

        utilityMenu = printerMenu.addMenu('Utilities')
        self.utilityMenu = utilityMenu
        utilityMenu.addAction(self.flashAction)
        utilityMenu.addAction(self.uploadFileAction)
        utilityMenu.addAction(self.printFileAction)
        utilityMenu.addAction(self.processImageAction)
        utilityMenu.addAction(self.ratePrintAction)
        utilityMenu.addAction(self.dryAction)

        helpMenu = menubar.addMenu('Help')
        helpMenu.addAction(self.updateAction)
        helpMenu.addSeparator()
        aboutAction = QtGui.QAction('&About', self)
        aboutAction.triggered.connect(self.aboutActionTriggered)
        helpMenu.addAction(aboutAction)

        self.statusBar().showMessage('Looking for printer...')

        self.disableAllButtonsExceptConnect()

        # Create the Print tab
        self.printWidget = QtGui.QWidget(self)
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.addWidget(self.printView)
        self.printWidget.setLayout(horizontalLayout)

        # Main Window Setup
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setTabPosition(QtGui.QTabWidget.South)
        self.tabWidget.addTab(self.printWidget, "Layout")
        self.tabWidget.addTab(self.console, "Console") # always last
        self.setCentralWidget(self.tabWidget)

        self.printingCompleted = False

        QtCore.QTimer.singleShot(100, self.monitor)
        QtCore.QTimer.singleShot(3000, self.nowAndThen)

        self.setGeometry(300, 300, 1000, 800)
        self.setWindowTitle('Argentum Control')
        self.show()

    def startUpdateLoop(self):
        updateThread = threading.Thread(target=self.updateLoop)
        updateThread.start()

    def updateLoop(self):
        try:
            time.sleep(3)
            data = {
                "printernum": self.getPrinterNumber(),
                "ts_processing_images": self.getTimeSpentProcessingImages(),
                "ts_sending_files": self.getTimeSpentSendingFiles(),
                "ts_printing": self.getTimeSpentPrinting(),
                "version": BASEVERSION,
                "platform": sys.platform
               }
            r = requests.post("https://www.cartesianco.com/feedback/run.php", data=data, verify=CA_CERTS)
            result = r.text
            tagVS = '#VersionStart#'
            tagVE = '#VersionEnd#'
            if result.find(tagVS) != -1:
                tagV = result[result.find(tagVS) + len(tagVS):]
                if tagV.find(tagVE) != -1:
                    tagV = tagV[:tagV.find(tagVE)]
                    tagV = tagV.strip()
                    self.latestVersion = tagV
                    print("Latest version is " + self.latestVersion)
            tagIUS = "#InlineUpdateStart#"
            tagIUE = "#InlineUpdateEnd#"
            if result.find(tagIUS) != -1:
                tagIU = result[result.find(tagIUS) + len(tagIUS):]
                if tagIU.find(tagIUE) != -1:
                    tagIU = tagIU[:tagIU.find(tagIUE)]
                    tagIU = tagIU.strip()
                    if tagIU.startswith("https://") or tagIU.startswith("http://"):
                        self.inlineUpdateUrl = tagIU
                        print("Inline update url is " + self.inlineUpdateUrl)
            return True
        except Exception as e:
            print("updateLoop exception: {}".format(e))
            return False

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

    def showImageSelectionDialog(self):
        return str(QtGui.QFileDialog.getOpenFileName(self, 'Select an image to process', self.lastImportDir, "Image Files (*.png *.xpm *.jpg *.svg *.bmp);;All Files (*.*)"))

    def processImage(self, inputFileName=None):
        if inputFileName == None:
            inputFileName = self.showImageSelectionDialog()

        if inputFileName:
            self.lastImportDir = os.path.dirname(inputFileName)

            self.processImageProgressPercent = None
            self.processImageProgressCancel = False
            self.processImageProgress = QtGui.QProgressDialog(self)
            self.processImageProgress.setWindowTitle("Processing")
            self.processImageProgress.setLabelText(os.path.basename(inputFileName))
            self.processImageProgress.show()
            QtCore.QTimer.singleShot(100, self.processImageProgressUpdater)

            self.processImageThread = threading.Thread(target=self.processImageLoop)
            self.processImageThread.filename = inputFileName
            self.processImageThread.outFilename = None
            self.processImageThread.start()

    def processImageLoop(self):
            inputFileName = self.processImageThread.filename
            print('Processing Image ' + inputFileName)
            baseName = os.path.basename(inputFileName)
            if baseName.find('.') != -1:
                baseName = baseName[:baseName.find('.')]
            baseName = baseName + '.hex'
            outputFileName = os.path.join(self.filesDir, baseName)
            self.processImageThread.outFilename = outputFileName
            print('Writing to ' + outputFileName)
            ip = self.getImageProcessor()
            ip.sliceImage(inputFileName, outputFileName, progressFunc=self.processImageProgressFunc)

    def processImageProgressFunc(self, pos, size):
        if self.processImageProgressCancel:
            return False
        self.processImageProgressPercent = pos * 100.0 / size
        return True

    printFileAfterProcessing = False
    def processImageProgressUpdater(self):
        if self.processImageProgress.wasCanceled():
            self.processImageProgressCancel = True
            self.printFileAfterProcessing = False
            return
        if self.processImageProgressPercent:
            self.processImageProgress.setValue(self.processImageProgressPercent)
            if self.processImageProgressPercent == 100:
                if self.printFileAfterProcessing:
                    self.printFileAfterProcessing = False
                    self.printFile(self.processImageThread.outFilename)
                self.processImageProgressPercent = None
                return
            self.processImageProgressPercent = None
        QtCore.QTimer.singleShot(100, self.processImageProgressUpdater)

    def appendOutput(self, output):
        self.outputView.append(output)
        # Allow the gui to update during long processing
        QtGui.QApplication.processEvents()
        if output.find('+Print complete') != -1:
            self.printComplete()

    def nowAndThen(self):
        QtCore.QTimer.singleShot(3000, self.nowAndThen)
        if not self.naggedUpdate:
            self.nagUpdate()
        if self.printingCompleted:
            self.printingCompleted = False
            self.printView.ratePrintActionTriggered()

    def monitor(self):
        data = self.printer.monitor()
        if data:
            self.appendOutput(data.decode('utf-8', 'ignore'))
        QtCore.QTimer.singleShot(100, self.monitor)

    ### Button Functions ###

    def rollerCalibrationActionTriggered(self):
        rollerDialog = RollerCalibrationDialog(self, None)
        rollerDialog.exec_()

    def preferencesActionTriggered(self):
        pass

    def aboutActionTriggered(self):
        QtGui.QMessageBox.information(self,
                        "CartesianCo Argentum Control",
                        "This software is used to control the Argentum circuit board printer.\n\nYou are running version {}.".format(BASEVERSION))

    def uploadProgressFunc(self, pos, size):
        if self.uploadProgressCancel:
            return False
        self.uploadProgressPercent = pos * 100.0 / size
        return True

    printOnline = False
    def uploadLoop(self):
        uploadStart = time.time()
        self.printer.send(self.uploadThread.filename,
                          progressFunc=self.uploadProgressFunc,
                          printOnline=self.printOnline)
        self.printOnline = False
        uploadEnd = time.time()
        self.addTimeSpentSendingFiles(uploadEnd - uploadStart)

    def uploadProgressUpdater(self):
        if self.uploadProgress.wasCanceled():
            self.uploadProgressCancel = True
            return
        if self.uploadProgressPercent:
            self.uploadProgress.setValue(self.uploadProgressPercent)
            self.uploadProgressPercent = None
        QtCore.QTimer.singleShot(100, self.uploadProgressUpdater)

    def uploadFile(self, filename=None):
        title = 'Hex file to upload'
        if self.printOnline:
            title = "File to print"
        if filename == None:
            filename = QtGui.QFileDialog.getOpenFileName(self, title, self.filesDir, "Hex files (*.hex);; All files (*)")
            filename = str(filename)
        if filename:
            if self.printOnline and not filename.endswith(".hex"):
                self.printFileAfterProcessing = True
                self.processImage(filename)
                return
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

    def uploadFileActionTriggered(self):
        self.uploadFile()

    def printFile(self, filename=None):
        self.printOnline = True
        self.uploadFile(filename)

    def printFileActionTriggered(self):
        self.printFile()

    def updateActionTriggered(self):
        if not self.updateLoop():
            QtGui.QMessageBox.information(self,
                        "Software update",
                        "The software was unable to connect to the Internet. Ensure your Internet connection is working and that any firewall programs are allowing the software to access the Internet.")
            return

        self.naggedUpdate = False
        if not self.nagUpdate():
            QtGui.QMessageBox.information(self,
                        "Software update",
                        "You are running the latest version of the software.")

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
        #self.processImageButton.setEnabled(enabled)

    def disableAllButtons(self):
        self.enableAllButtons(False)

    def disableAllButtonsExceptConnect(self):
        self.disableAllButtons()
        self.connectButton.setEnabled(True)

    def versionIsNewer(self, latest):
        if latest.find('+') != -1:
            latest = latest[:latest.find('+')]
        parts = latest.split('.')
        version = BASEVERSION.split('.')
        if int(parts[0]) > int(version[0]):
            return True
        if int(parts[0]) == int(version[0]):
            if int(parts[1]) > int(version[1]):
                return True
            if int(parts[1]) == int(version[1]):
                if int(parts[2]) > int(version[2]):
                    return True
        return False

    naggedUpdate = False
    def nagUpdate(self):
        if self.latestVersion == None:
            return None
        self.naggedUpdate = True

        if not self.versionIsNewer(self.latestVersion):
            return False
        if self.inlineUpdateUrl == None:
            return False

        reply = QtGui.QMessageBox.question(self, 'Software update',
            'There is a newer version of the software available. It is advisable that you update to get the newest features and bug fixes. Would you like to do this now?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.Yes)

        if reply == QtGui.QMessageBox.Yes:
            self.startInlineUpdate()
            #else:
            #    webbrowser.open("http://www.cartesianco.com/software/", 2)

        return True

    def startInlineUpdate(self):
        self.downloadProgressPercent = None
        self.downloadProgressCancel = False
        self.downloadProgress = QtGui.QProgressDialog(self)
        self.downloadProgress.setWindowTitle("Updating")
        self.downloadProgress.setLabelText("Downloading version " + self.latestVersion)
        self.downloadProgress.show()
        QtCore.QTimer.singleShot(100, self.downloadProgressUpdater)

        self.downloadThread = threading.Thread(target=self.downloadLoop)
        self.downloadThread.start()

    def downloadLoop(self):
        tmpdir = tempfile.mkdtemp()
        update_filename = tmpdir + "/update.zip"
        print("Writing update to " + update_filename)
        f = open(update_filename, "wb")

        r = requests.get(self.inlineUpdateUrl, stream=True, verify=CA_CERTS)
        total_length = r.headers.get('content-length')
        if total_length == None:
            self.downloadError = True
            return

        total_length = int(total_length)
        dl = 0
        for data in r.iter_content():
            dl += len(data)
            f.write(data)
            self.downloadProgressPercent = dl * 80.0 / total_length
            if self.downloadProgressCancel:
                return
        f.close()

        print("Update downloaded. Extracting..")

        new_files_dir = tmpdir + "/new"
        z = zipfile.ZipFile(update_filename, 'r')
        z.extractall(new_files_dir)
        z.close()

        # What kind of install are we?
        site_packages = None
        resources_dir = os.getcwd()
        gui_in_site_packages = False
        rename_gui_to = None
        program_path = sys.argv[0]
        cur_dir_name = os.path.basename(os.getcwd())
        if cur_dir_name == "src":
            print("This looks like a source build, use git to update.")
            self.downloadProgressPercent = 100.0
            return
        elif cur_dir_name.lower() == "resources":
            print("This looks like a Mac build.")
            site_packages = "lib/python2.7/site-packages.zip"
            program_path = "../MacOS/gui"
        elif os.path.exists("gui.exe"):
            print("This looks like a Windows build.")
            site_packages = "library.zip"
            gui_in_site_packages = True
            rename_gui_to = 'gui__main__.py'
            program_path = "gui.exe"
        else:
            print("This looks like a Linux build.")

        resources = os.listdir(new_files_dir)
        if site_packages:
            print("Extracting site packages..")
            site_packages_dir = tmpdir + "/site_packages"
            z = zipfile.ZipFile(site_packages, 'r')
            z.extractall(site_packages_dir)
            z.close()

            print("Copy files to site packages..")
            resources = []
            for fname in os.listdir(new_files_dir):
                if not fname.endswith(".py"):
                    resources.append(fname)
                    continue
                if fname == "gui.py":
                    if not gui_in_site_packages:
                        resources.append(fname)
                        continue
                    if rename_gui_to:
                        shutil.copy(new_files_dir + "/" + fname,
                                    site_packages_dir + "/" + rename_gui_to)
                        continue
                shutil.copy(new_files_dir + "/" + fname, site_packages_dir)

            print("Zipping up the site packages..")
            z = zipfile.ZipFile(tmpdir + "/" + os.path.basename(site_packages), 'w')
            todo = os.listdir(site_packages_dir)
            for fname in todo:
                if os.path.isdir(site_packages_dir + "/" + fname):
                    for sfname in os.listdir(site_packages_dir + "/" + fname):
                        todo.append(fname + "/" + sfname)
                else:
                    z.write(site_packages_dir + "/" + fname, fname)
            z.close()

            print("Overwriting the site packages..")
            shutil.copy(tmpdir + "/" + os.path.basename(site_packages), site_packages)

        print("Overwriting the resources..")
        for fname in resources:
            shutil.copy(new_files_dir + "/" + fname, resources_dir)

        print("Removing temporary files.")
        self.downloadProgressPercent = 90.0
        shutil.rmtree(tmpdir)

        print("Restarting.")
        self.downloadProgressPercent = 100.0
        if self.printer.connected:
            self.autoConnect = False
            self.printer.disconnect()
        if program_path.endswith(".py"):
            os.chmod(program_path, stat.S_IRWXU)
        time.sleep(1.5)
        os.execv(program_path, [program_path])

    def downloadProgressUpdater(self):
        if self.downloadProgress.wasCanceled():
            self.downloadProgressCancel = True
            return
        if self.downloadProgressPercent:
            self.downloadProgress.setValue(self.downloadProgressPercent)
            if self.downloadProgressPercent == 80.0:
                self.downloadProgress.setLabelText("Applying update...")
            if self.downloadProgressPercent == 90.0:
                self.downloadProgress.setLabelText("Cleaning up...")
            if self.downloadProgressPercent == 100.0:
                self.downloadProgress.setLabelText("Restarting.")
            self.downloadProgressPercent = None
        QtCore.QTimer.singleShot(100, self.downloadProgressUpdater)

    naggedFirmwareUpgrade = False
    checkFlashVersion = None
    def nagFirmwareUpgrade(self):
        if self.naggedFirmwareUpgrade:
            return
        self.naggedFirmwareUpgrade = True
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
        inputFilename = self.showImageSelectionDialog()
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
        self.printFileAction.setEnabled(enabled)
        self.rollerCalibrationAction.setEnabled(enabled)

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
                    self.printerConnected()
                else:
                    QtGui.QMessageBox.information(self, "Cannot connect to printer", self.printer.lastError)
                    self.statusBar().showMessage('Connection error.')
        self.updatePortList()

    def printerConnected(self):
        self.connectButton.setText('Disconnect')

        self.enableAllButtons()
        self.enableConnectionSpecificControls(True)
        self.statusBar().showMessage('Connected.')
        self.sentVolt = False

        if self.printer.version != None:
            for line in self.printer.junkBeforeVersion:
                self.appendOutput(line)
            self.appendOutput("Printer is running: " + self.printer.version)

        if self.printer.printerNumber == "NOT_SET":
            self.askForPrinterNumber()

        options = self.printer.getOptions()
        if options != None:
            for key, value in options.items():
                self.options[key] = value
            save_options(self.options)

        self.printer.home()

        if (self.printer.version != None and
                is_older_firmware(self.printer.version)):
            self.nagFirmwareUpgrade()

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
                if self.autoConnect and not self.printer.connected and curPort != NO_PRINTER:
                    self.autoConnect = False
                    self.autoConnected = False
                    QtCore.QTimer.singleShot(100, self.autoConnectUpdater)
                    self.autoConnectThread = threading.Thread(target=self.autoConnectLoop)
                    self.autoConnectThread.port = str(curPort)
                    self.autoConnectThread.start()

    def autoConnectUpdater(self):
        if self.autoConnected:
            if self.printer.connected:
                self.printerConnected()
                self.autoConnect = True
            return
        QtCore.QTimer.singleShot(100, self.autoConnectUpdater)

    def autoConnectLoop(self):
        port = self.autoConnectThread.port
        print("autoConnectLoop running with port={}".format(port))
        if port != NO_PRINTER:
            if self.printer.connect(port=port):
                self.autoConnected = True
            else:
                print("Failed to connect to printer: " + self.printer.lastError)

    def viewSwitchActionTriggered(self):
        if self.viewSwitchAction.text() == "Console":
            self.tabWidget.setCurrentWidget(self.console)
            self.viewSwitchAction.setText("Layout")
        else:
            self.tabWidget.setCurrentWidget(self.printWidget)
            self.viewSwitchAction.setText("Console")

    def processImageButtonPushed(self):
        self.processImage()

    def processImageActionTriggered(self):
        self.processImage()

    def askForPrinterNumber(self):
        getPrinterNumberDialog = GetPrinterNumberDialog(self)
        getPrinterNumberDialog.exec_()

    def updatePosDisplay(self, pos=None):
        if pos == None:
            if not self.printer.connected:
                return
            if self.printer.getTimeSinceLastCommand() < 1:
                return
            if self.printing or self.printer.printing:
                return
            pos = self.printer.getPosition()
            if pos == None:
                return
        self.lastPos = pos
        (xmm, ymm, x, y) = pos
        self.posLabel.setText("{}, {} mm {}, {} steps".format(xmm, ymm, x, y))
        self.printView.updatePrintHeadPos(pos)

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
        self.printer.moveTo(x, y)

    ### Command Functions ###

    def rollerCommand(self, cmd):
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
            self.turnLightsOn()
            self.sendPrintCommand()

    def stopButtonPushed(self):
        self.appendOutput('Stop!')
        self.printer.emergencyStop()
        self.printComplete()

    def printComplete(self):
        self.printing = False
        self.printButton.setText('Print')
        if self.printStartTime:
            printEndTime = time.time()
            self.addTimeSpentPrinting(printEndTime - self.printStartTime)
            self.printStartTime = None
        self.printingCompleted = True

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
        self.printStartTime = time.time()
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
        if self.commandField.hasFocus():
            return
        self.decrementX()

    def shortcutRight(self):
        self.incrementX()

    def shortcutUp(self):
        if self.commandField.hasFocus():
            self.commandField.event(QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                    QtCore.Qt.Key_Up,
                                                    QtCore.Qt.NoModifier))
            return
        self.incrementY()

    def shortcutDown(self):
        if self.commandField.hasFocus():
            self.commandField.event(QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                    QtCore.Qt.Key_Down,
                                                    QtCore.Qt.NoModifier))
            return
        self.decrementY()

    def shortcutHome(self):
        self.homeButtonPushed()

    def shortcutMinus(self):
        self.printer.command('--')

    def shortcutPlus(self):
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

    def getPrinterNumber(self):
        if self.printer.connected:
            if self.printer.printerNumber != None:
                return self.printer.printerNumber

            pnum = self.printer.getPrinterNumber()
            if pnum != None:
                return pnum

        try:
            return self.options["printer_number"]
        except:
            return None

    def setPrinterNumber(self, val):
        if self.printer.connected:
            self.printer.setPrinterNumber(val)
        self.options["printer_number"] = val
        save_options(self.options)
        self.startUpdateLoop()

    def getTimeSpent(self, name):
        cur = 0
        try:
            cur = self.options[name]
        except:
            pass
        return cur

    def addTimeSpent(self, name, val):
        self.options[name] = self.getTimeSpent(name) + val
        save_options(self.options)

    def getTimeSpentProcessingImages(self):
        return self.getTimeSpent("ts_processing_images")
    def addTimeSpentProcessingImages(self, val):
        self.addTimeSpent("ts_processing_images", val)

    def getTimeSpentSendingFiles(self):
        return self.getTimeSpent("ts_sending_files")
    def addTimeSpentSendingFiles(self, val):
        self.addTimeSpent("ts_sending_files", val)

    def getTimeSpentPrinting(self):
        return self.getTimeSpent("ts_printing")
    def addTimeSpentPrinting(self, val):
        self.addTimeSpent("ts_printing", val)

    def closeEvent(self, evt):
        sys.exit(0)

def main():
    print("starting...")
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
