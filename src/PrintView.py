#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control PrintView

author: Trent Waddington
"""

import sys
import os
import threading
import time
from PyQt4 import QtGui, QtCore, QtSvg
from gerber import Gerber
import requests
from setup import VERSION, BASEVERSION, CA_CERTS
import tempfile

printPlateDesignScale = [1.0757, 1.2256] # * printArea
imageScale            = [ 23.70,  23.70] # * print = pixels

# A kind of annoying Rect
# Note: (0,0) is the bottom left corner of the printer
# All measurements are in millimeters
class PrintRect:
    def __init__(self, left, bottom, width, height):
        self.left   = float(left)
        self.bottom = float(bottom)
        self.width  = float(width)
        self.height = float(height)

class PrintImage(PrintRect):
    def __init__(self, pixmap, filename):
        self.pixmap = pixmap
        self.filename = filename
        self.left = 0.0
        self.bottom = 0.0
        self.width = pixmap.width() / imageScale[0]
        self.height = pixmap.height() / imageScale[1]
        self.lastResized = None
        self.screenRect = None

        filename = os.path.basename(filename)
        if filename.find('.') != -1:
            filename = filename[:filename.find('.')]
        self.hexFilename = filename + ".hex"

    def pixmapRect(self):
        return QtCore.QRectF(self.pixmap.rect())

class PrintCanceledException(Exception):
    pass

class PrintOptionsDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setWindowTitle("Print Options")
        mainLayout = QtGui.QVBoxLayout()
        self.printView = parent
        self.argentum = parent.argentum

        layout = QtGui.QHBoxLayout()
        layout.addWidget(QtGui.QLabel("Print each image"))
        self.passes = QtGui.QSpinBox(self)
        self.passes.setMinimum(1)
        layout.addWidget(self.passes)
        layout.addWidget(QtGui.QLabel("times"))
        mainLayout.addLayout(layout)

        self.useRollers = QtGui.QCheckBox("Dry the print after each pass")
        self.useRollers.setChecked(self.argentum.getOption("use_rollers", True))
        mainLayout.addWidget(self.useRollers)

        layout = QtGui.QHBoxLayout()
        cancelButton = QtGui.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton)
        printButton = QtGui.QPushButton("Print")
        printButton.clicked.connect(self.accept)
        layout.addWidget(printButton)
        mainLayout.addLayout(layout)

        printButton.setDefault(True)

        self.setLayout(mainLayout)

    def getPasses(self):
        return self.passes.value()

    def getUseRollers(self):
        return self.useRollers.isChecked()

class PrintProgressDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.printView = parent
        mainLayout = QtGui.QVBoxLayout()
        self.label = QtGui.QLabel("")
        self.label.setAlignment(QtCore.Qt.AlignHCenter)
        mainLayout.addWidget(self.label)

        self.progressBar = QtGui.QProgressBar(self)
        self.progressBar.setOrientation(QtCore.Qt.Horizontal)
        mainLayout.addWidget(self.progressBar)

        layout = QtGui.QHBoxLayout()
        self.pauseButton = QtGui.QPushButton("Pause")
        self.pauseButton.clicked.connect(self.pause)
        layout.addWidget(self.pauseButton)
        self.cancelButton = QtGui.QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)
        layout.addWidget(self.cancelButton)
        mainLayout.addLayout(layout)

        self.cancelButton.setDefault(True)

        self.setLayout(mainLayout)

        self.paused = False
        self.canceled = False

    def wasCanceled(self):
        return self.canceled

    def setLabelText(self, text):
        self.label.setText(text)

    def setValue(self, value):
        self.progressBar.setValue(value)
        if value == 100:
            self.hide()

    def cancel(self):
        self.canceled = True

    def pause(self):
        if self.paused:
            self.paused = False
            self.pauseButton.setText("Pause")
        else:
            self.paused = True
            self.pauseButton.setText("Resume")

    def closeEvent(self, e):
        self.cancel()

class RateYourPrintDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setWindowTitle("Rate Your Print")
        mainLayout = QtGui.QVBoxLayout()
        self.argentum = parent.argentum

        info = QtGui.QLabel("How was your print?")
        mainLayout.addWidget(info)
        mainLayout.addWidget(QtGui.QLabel(" "))
        layout = QtGui.QHBoxLayout()
        for n in range(1, 6):
            label = QtGui.QLabel(str(n))
            if n == 1:
                label.setAlignment(QtCore.Qt.AlignLeft)
            if n == 2:
                label.setAlignment(QtCore.Qt.AlignLeft)
                layout.addSpacing(45)
            if n == 3:
                label.setAlignment(QtCore.Qt.AlignHCenter)
            if n == 4:
                label.setAlignment(QtCore.Qt.AlignRight)
            if n == 5:
                layout.addSpacing(45)
                label.setAlignment(QtCore.Qt.AlignRight)
            layout.addWidget(label)
        mainLayout.addLayout(layout)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setRange(1, 5)
        self.slider.setValue(3)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(self.slider.TicksAbove)
        mainLayout.addWidget(self.slider)
        mainLayout.addWidget(QtGui.QLabel(" "))
        info = QtGui.QLabel("Your feedback is important. Please let us know how we can make your print better.")
        mainLayout.addWidget(info)
        self.comments = QtGui.QTextEdit(self)
        mainLayout.addWidget(self.comments)
        layout = QtGui.QHBoxLayout()
        info = QtGui.QLabel("Your printer number:")
        layout.addWidget(info)
        self.printerNum = QtGui.QLineEdit(self)
        if self.argentum.getPrinterNumber():
            self.printerNum.setText(self.argentum.getPrinterNumber())
        layout.addWidget(self.printerNum)
        self.printerNum.setToolTip("Look on the back of your printer.")
        mainLayout.addLayout(layout)

        layout = QtGui.QHBoxLayout()
        cancelButton = QtGui.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton)
        self.sendButton = QtGui.QPushButton("Send Report")
        self.sendButton.clicked.connect(self.sendReport)
        layout.addWidget(self.sendButton)
        mainLayout.addLayout(layout)

        self.sendButton.setDefault(True)

        self.setLayout(mainLayout)

    def sendLoop(self):
        firmware = ""
        if self.argentum.printer != None:
            firmware = self.argentum.printer.version
        data = {"rate": self.rate,
                "comments": self.commentText,
                "installnum": self.argentum.getInstallNumber(),
                "printernum": self.printerNumText,
                "ts_processing_images": self.argentum.getTimeSpentProcessingImages(),
                "ts_sending_files": self.argentum.getTimeSpentSendingFiles(),
                "ts_printing": self.argentum.getTimeSpentPrinting(),
                "version": BASEVERSION,
                "firmware": firmware
               }
        r = requests.post("https://www.cartesianco.com/feedback/print.php", data=data, verify=CA_CERTS)
        print(r.text)

    def sendReport(self):
        self.sendButton.setText("Sending...")
        self.printerNumText = str(self.printerNum.text())
        if self.printerNumText != "":
            self.argentum.setPrinterNumber(self.printerNumText)
        self.rate = self.slider.sliderPosition()
        self.commentText = str(self.comments.toPlainText())
        updateThread = threading.Thread(target=self.sendLoop)
        updateThread.start()
        self.accept()

class PrintView(QtGui.QWidget):
    layout = None
    layoutChanged = False
    printThread = None
    dragging = None
    resizing = None
    selection = None

    def __init__(self, argentum):
        super(PrintView, self).__init__()
        self.argentum = argentum
        self.lastRect = QtCore.QRect()
        self.progress = PrintProgressDialog(self)
        self.progress.setWindowTitle("Printing")
        self.progress.hide()
        QtCore.QTimer.singleShot(100, self.progressUpdater)
        self.fanSpeed = 4
        QtCore.QTimer.singleShot(1000 / self.fanSpeed, self.fanAnimator)

        self.printPlateArea = PrintRect(0, 0, 285, 255)
        self.printArea = PrintRect(24, 73, 247, 127)
        self.printLims = PrintRect(10, 14, 157, 98)
        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")
        self.trashCan         = QtSvg.QSvgRenderer("trashCan.svg")
        self.trashCanOpen     = QtSvg.QSvgRenderer("trashCanOpen.svg")
        self.showTrashCanOpen = False
        height = self.printArea.height * printPlateDesignScale[1]
        self.printPlateDesignArea = PrintRect(12,
                    50,
                    self.printArea.width * printPlateDesignScale[0],
                    height)
        self.images = []
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self.kerfPen = QtGui.QPen(QtGui.QColor(0, 0, 0))
        self.kerfPen.setWidth(10)
        self.kerfPen.setCapStyle(QtCore.Qt.RoundCap)

        self.kerfOutlinePen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        self.kerfOutlinePen.setWidth(13)
        self.kerfOutlinePen.setCapStyle(QtCore.Qt.RoundCap)

        self.fanImage1 = QtGui.QPixmap("fan1.png")
        self.fanImage2 = QtGui.QPixmap("fan2.png")
        self.printHeadPixmap = QtGui.QPixmap("printhead.png")

        self.printHeadImage = PrintImage(self.printHeadPixmap, "")
        self.printHeadImage.minLeft = -24 + 10
        self.printHeadImage.left = self.printHeadImage.minLeft
        self.printHeadImage.minBottom = -73 + 11
        self.printHeadImage.bottom = self.printHeadImage.minBottom
        #self.printHeadImage.width = 95
        #self.printHeadImage.height = 90
        self.printHeadImage.width = 98
        self.printHeadImage.height = 95
        self.images.append(self.printHeadImage)

        self.colorPicker = QtGui.QColorDialog()
        self.pickColorFor = None
        self.colorPicker.colorSelected.connect(self.colorPicked)
        self.showingPrintHead = False
        self.showingPrintLims = True

        self.printButton = QtGui.QPushButton("Print")
        self.printButton.clicked.connect(self.startPrint)
        mainLayout = QtGui.QVBoxLayout()
        layout = QtGui.QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.printButton)
        layout.addStretch()
        mainLayout.addStretch()
        mainLayout.addLayout(layout)
        self.setLayout(mainLayout)


    def updatePrintHeadPos(self, pos):
        if self.dragging == self.printHeadImage:
            return
        (xmm, ymm, x, y) = pos
        self.printHeadImage.left = self.printHeadImage.minLeft + xmm
        self.printHeadImage.bottom = self.printHeadImage.minBottom + ymm
        self.printHeadImage.screenRect = None
        self.update()

    def showPrintHeadActionTriggered(self):
        if self.showingPrintHead:
            self.showingPrintHead = False
        else:
            self.showingPrintHead = True
            self.argentum.updatePosDisplay()
        self.update()

    def showPrintLimsActionTriggered(self):
        if self.showingPrintLims:
            self.showingPrintLims = False
        else:
            self.showingPrintLims = True
        self.update()

    def ratePrintActionTriggered(self):
        rateDialog = RateYourPrintDialog(self)
        rateDialog.exec_()

    def dryActionTriggered(self):
        if self.printThread != None:
            print("Already printing!")
            return

        self.printCanceled = False
        self.progress = PrintProgressDialog(self)
        self.progress.setWindowTitle("Drying")
        self.progress.setLabelText("Starting up...")
        self.progress.setValue(0)
        self.progress.show()

        self.printThread = threading.Thread(target=self.dryingLoop)
        self.printThread.dryingOnly = True
        self.printThread.start()

    def dryingLoop(self):
        try:
            if self.argentum.options["use_rollers"] == False:
                return
        except:
            pass
        print("Drying mode on.")

        try:
            printer = self.argentum.printer
            printer.command("l E", expect='rollers')

            for image in self.images:
                if image == self.printHeadImage:
                    continue
                print("Jacketing drying.")
                self.setProgress(labelText="Drying " + image.hexFilename)
                pos = self.printAreaToMove(image.left + image.width - 60, image.bottom + 30)
                x = pos[0]
                y = pos[1]
                sy = y
                while y - sy < image.height * 80:
                    while self.progress.paused:
                        time.sleep(0.5)
                    printer.moveTo(x, y, withOk=True)
                    printer.waitForResponse(timeout=10, expect='Ok')
                    printer.command("l d", expect='rollers')
                    time.sleep(1.5)
                    left = x - image.width * 80
                    if left < 0:
                        left = 0
                    while self.progress.paused:
                        time.sleep(0.5)
                    printer.moveTo(left, y, withOk=True)
                    printer.waitForResponse(timeout=10, expect='Ok')
                    printer.command("l r", expect='rollers')
                    time.sleep(1.5)
                    y = y + 30 * 80

            printer.command("l e", expect='rollers')
        finally:
            if self.printThread.dryingOnly:
                self.printThread = None
                self.setProgress(percent=100)
                self.argentum.printer.home()

        print("Your jacket is now dry.")

    def calcScreenRects(self):
        if self.lastRect == self.rect():
            for image in self.images:
                if image.screenRect == None:
                    image.screenRect = self.printAreaToScreen(image)
            return
        self.lastRect = self.rect()

        # Ensure correct aspect ratio
        aspectRect = QtCore.QRectF(self.rect())
        aspectRatio = aspectRect.width() / aspectRect.height()
        desiredAspectRatio = (self.printPlateArea.width /
                              self.printPlateArea.height)
        #print("window {} x {}".format(aspectRect.width(), aspectRect.height()))
        #print("aspect ratio {}".format(aspectRatio))
        #print("desired aspect ratio {}".format(desiredAspectRatio))

        if aspectRatio < desiredAspectRatio:
            height = aspectRect.height() * (aspectRatio / desiredAspectRatio)
            #print("calculated height {}".format(height))
            #print("calculated aspect ratio {}".format(aspectRect.width() / height))
            aspectRect.setTop((aspectRect.height() - height) / 2)
            aspectRect.setHeight(height)
        else:
            width = aspectRect.width() / (aspectRatio / desiredAspectRatio)
            #print("calculated width {}".format(width))
            #print("calculated aspect ratio {}".format(width / aspectRect.height()))
            aspectRect.setLeft((aspectRect.width() - width) / 2)
            aspectRect.setWidth(width)

        #print("printPlateRect is {}, {} {} x {}".format(aspectRect.left(), 
        #                                             aspectRect.top(),
        #                                             aspectRect.width(),
        #                                             aspectRect.height()))
        self.printPlateRect = aspectRect

        # Now we can make the screen rects
        self.printPlateDesignRect = self.printToScreen(self.printPlateDesignArea)
        for image in self.images:
            image.screenRect = self.printAreaToScreen(image)
        self.trashCanRect = QtCore.QRectF(
           (self.printPlateDesignRect.left() +
            self.printPlateDesignRect.width() * 19 / 21),
           (self.printPlateDesignRect.top() +
            self.printPlateDesignRect.height() * 5 / 7),
           self.printPlateDesignRect.width() / 8,
           self.printPlateDesignRect.height() / 5)

        ppdr = self.printPlateDesignRect
        my = 30
        mx = 30
        self.leftLightsRect = QtCore.QRectF(ppdr.left() - mx - 10, ppdr.top() - my, mx, ppdr.height() + my*2)
        self.rightLightsRect = QtCore.QRectF(ppdr.right() + mx / 2, ppdr.top() - my, mx, ppdr.height() + my*2)
        self.bottomLightRects = []
        mmx = mx/3
        self.bottomLightRects.append(QtCore.QRectF(ppdr.left() + ppdr.width()*0.05, self.leftLightsRect.bottom() + my, mmx, mmx))
        self.bottomLightRects.append(QtCore.QRectF(ppdr.left() + ppdr.width()/2 - mmx/2, self.leftLightsRect.bottom() + my, mmx, mmx))
        self.bottomLightRects.append(QtCore.QRectF(ppdr.right() - ppdr.width()/13, self.leftLightsRect.bottom() + my, mmx, mmx))

        self.leftKerfRect = QtCore.QRectF(ppdr.left() - mx*2, ppdr.bottom(), mx*2, my*2 + mmx*2)
        self.rightKerfRect = QtCore.QRectF(ppdr.right(), ppdr.bottom(), mx*2, my*2 + mmx*2)

        self.fanImage = self.fanImage1
        fw = ppdr.width() / 13
        self.leftFanRect = QtCore.QRectF(ppdr.left(), ppdr.top() - fw*2, fw, fw)
        self.rightFanRect = QtCore.QRectF(ppdr.right() - fw, ppdr.top() - fw*2, fw, fw)

    def printToScreen(self, printRect):
        #print("printRect {}, {} {} x {}".format(printRect.left,
        #                                        printRect.bottom,
        #                                        printRect.width,
        #                                        printRect.height))
        #print("printPlateArea {} x {}".format(self.printPlateArea.width,
        #                                      self.printPlateArea.height))
        left   = (self.printPlateRect.left() +
                  printRect.left / self.printPlateArea.width
                               * self.printPlateRect.width())
        top    = (self.printPlateRect.top() + self.printPlateRect.height() -
                  (printRect.bottom + printRect.height)
                                 / self.printPlateArea.height
                               * self.printPlateRect.height())
        width  = (printRect.width / self.printPlateArea.width
                               * self.printPlateRect.width())
        height = (printRect.height / self.printPlateArea.height
                               * self.printPlateRect.height())

        #print("on screen {}, {} {} x {}".format(left, top, width, height))

        return QtCore.QRectF(left, top, width, height)

    def printAreaToScreen(self, printRect):
        p = PrintRect(self.printArea.left + printRect.left,
                      self.printArea.bottom + printRect.bottom,
                      printRect.width, printRect.height)
        return self.printToScreen(p)

    def printAreaToMove(self, offsetX, offsetY):
        fudgeX = -80
        fudgeY = -560
        x = offsetX * 80 + fudgeX
        y = offsetY * 80 + fudgeY
        x = int(x)
        y = int(y)
        return (x, y)

    def screenToPrintArea(self, x, y):
        r = self.printToScreen(self.printArea)

        dx = x - r.left()
        dy = y - r.top()

        return (dx * self.printArea.width / r.width(),
                self.printArea.height - dy * self.printArea.height / r.height())

    def updateTitle(self):
        if self.layout:
            name = os.path.basename(self.layout)
            if name.find('.layout') == len(name)-7:
                name = name[:len(name)-7]
            self.argentum.setWindowTitle(name + " - Argentum Control")
        else:
            self.argentum.setWindowTitle("Argentum Control")

    def paintEvent(self, event):
        self.updateTitle()
        self.calcScreenRects()

        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setPen(QtGui.QColor(255, 255, 255))
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp, self.printPlateDesignRect)

        if self.showingPrintLims:
            printLimsScreenRect = self.printAreaToScreen(self.printLims)
            qp.drawRect(printLimsScreenRect)

        if self.dragging and self.dragging != self.printHeadImage:
            if self.showTrashCanOpen:
                self.trashCanOpen.render(qp, self.trashCanRect)
            else:
                self.trashCan.render(qp, self.trashCanRect)

        for image in self.images:
            if image == self.printHeadImage:
                continue
            qp.drawPixmap(image.screenRect, image.pixmap, image.pixmapRect())
        if self.showingPrintHead:
            image = self.printHeadImage
            qp.drawPixmap(image.screenRect, image.pixmap, image.pixmapRect())

        if self.argentum.printer.connected and self.argentum.printer.lightsOn:
            qp.setBrush(QtGui.QColor(0xff, 0xff, 0xff))
        else:
            qp.setBrush(QtGui.QColor(0xc6, 0xac, 0xac))
        qp.setPen(QtGui.QColor(0, 0, 0))
        qp.drawRoundedRect(self.leftLightsRect, 20.0, 15.0)
        qp.drawRoundedRect(self.rightLightsRect, 20.0, 15.0)
        for r in self.bottomLightRects:
            qp.drawRect(r)

        qp.setPen(self.kerfOutlinePen)
        qp.drawArc(self.leftKerfRect, 180*16, 90*16)
        qp.setPen(self.kerfPen)
        qp.drawArc(self.leftKerfRect, 180*16, 90*16)
        qp.setPen(self.kerfOutlinePen)
        qp.drawArc(self.rightKerfRect, 270*16, 90*16)
        qp.setPen(self.kerfPen)
        qp.drawArc(self.rightKerfRect, 270*16, 90*16)

        fanImage = self.fanImage1
        if self.argentum.printer.leftFanOn:
            fanImage = self.fanImage
        qp.drawPixmap(self.leftFanRect, fanImage, QtCore.QRectF(fanImage.rect()))
        fanImage = self.fanImage1
        if self.argentum.printer.rightFanOn:
            fanImage = self.fanImage
        qp.drawPixmap(self.rightFanRect, fanImage, QtCore.QRectF(fanImage.rect()))
        qp.end()

    def gerberToPixmap(self, inputFileName):
        try:
            f = open(inputFileName, "r")
            contents = f.read()
            f.close()
        except:
            return None
        if contents[:1] != "G" and contents[:1] != '%':
            return None
        g = Gerber()
        g.parse(contents)
        if len(g.errors) > 0:
            str = "Errors parsing Gerber file {}\n".format(inputFileName)
            for error in g.errors:
                lineno, msg = error
                str = str + "{}: {}\n".format(lineno, msg)
            QtGui.QMessageBox.information(self, "Invalid Gerber file", str)
            return False
        r = QtSvg.QSvgRenderer(QtCore.QByteArray(g.toSVG()))
        print("Gerber size {} x {} {}".format(g.width, g.height, g.units))
        if g.units == "inches":
            pixmap = QtGui.QPixmap(g.width  * 25.4 * imageScale[0],
                                   g.height * 25.4 * imageScale[1])
        else:
            pixmap = QtGui.QPixmap(g.width  * imageScale[0],
                                   g.height * imageScale[1])
        p = QtGui.QPainter(pixmap)
        r.render(p, QtCore.QRectF(pixmap.rect()))
        if pixmap.width() / imageScale[0] > 230 or pixmap.height() / imageScale[1] > 120:
            QtGui.QMessageBox.information(self, "Gerber file too big", "The design provided is too big for the print area. It will be resized to fit, but this is probably not what you want.")
        return pixmap

    def addImageFile(self, inputFileName):
        pixmap = QtGui.QPixmap(inputFileName)
        if pixmap == None or pixmap.isNull():
            pixmap = self.gerberToPixmap(inputFileName)
            if pixmap == False:
                return None
        if pixmap == None or pixmap.isNull():
            QtGui.QMessageBox.information(self, "Invalid image file", "Can't load image " + inputFileName)
            return None
        if inputFileName[-4:] == ".svg":
            # Assume SVG files are in millimeters already
            pixmap = pixmap.scaled(pixmap.width()  * imageScale[0],
                                   pixmap.height() * imageScale[1])
            r = QtSvg.QSvgRenderer(inputFileName)
            p = QtGui.QPainter(pixmap)
            r.render(p, QtCore.QRectF(pixmap.rect()))
        pi = PrintImage(pixmap, inputFileName)
        self.images.append(pi)
        self.ensureImageInPrintLims(pi)
        self.update()
        self.layoutChanged = True
        return pi

    def isImageProcessed(self, image):
        hexFilename = os.path.join(self.argentum.filesDir, image.hexFilename)
        if not os.path.exists(hexFilename):
            return False
        if os.path.getsize(hexFilename) == 0:
            return False
        hexModified = os.path.getmtime(hexFilename)
        if time.time() - hexModified > 7*24*60*60:
            return False
        imgModified = os.path.getmtime(image.filename)
        if imgModified < hexModified:
            if image.lastResized:
                return image.lastResized < hexModified
            return True
        return False

    def imageProgress(self, y, max_y):
        if self.printCanceled:
            return False
        self.setProgress(incPercent=(self.perImage / max_y))
        return True

    def sendProgress(self, pos, size):
        if self.printPaused:
            return "Pause"
        if self.printCanceled:
            return False
        self.setProgress(percent=(20 + self.perImage * pos / size))
        return True

    def processImage(self, image):
        ip = self.argentum.getImageProcessor()
        hexFilename = os.path.join(self.argentum.filesDir, image.hexFilename)
        try:
            size = None
            if image.lastResized != None:
                width  = image.width  * imageScale[0]
                height = image.height * imageScale[1]
                size = (int(width), int(height))
                print("resizing {} to {},{}.".format(hexFilename, size[0], size[1]))
                print("original size {},{}.".format(image.pixmap.width(), image.pixmap.height()))
                image.hexFilename = "{}-{}x{}.hex".format(
                                    image.hexFilename[:-4], size[0], size[1])
                hexFilename = os.path.join(self.argentum.filesDir,
                                           image.hexFilename)
                self.layoutChanged = True

            ip.sliceImage(image.pixmap.toImage(), hexFilename,
                            progressFunc=self.imageProgress,
                            size=size)
        except Exception as e:
            print("error processing {}: {}.".format(image.filename, e))
            self.setProgress(labelText="Error processing {}.".format(image.filename))
            print("removing {}.".format(hexFilename))
            os.remove(hexFilename)
            raise

    curPercent = 0
    percent = None
    labelText = None
    statusText = None
    missing = None
    printCanceled = False
    printPaused = False
    def setProgress(self, percent=None,
                          incPercent=None,
                          labelText=None,
                          statusText=None,
                          missing=None,
                          canceled=None):
        if self.printCanceled:
            raise PrintCanceledException()
        if percent:
            self.percent = percent
            self.curPercent = percent
        if incPercent:
            self.curPercent = self.curPercent + incPercent
            self.percent = self.curPercent
        if labelText:
            self.labelText = labelText
        if statusText:
            self.statusText = statusText
        if missing:
            canceled = True
            self.missing = missing
        if canceled:
            self.printCanceled = canceled

    def reportMissing(self, missing):
        # I swear on Poseidon's trident, one day I shall remove the need
        # for this Sneaker Net bullshit
        msgbox = QtGui.QMessageBox()
        msgbox.setWindowTitle("Sneaker Net Required.")
        msgbox.setText("One or more files are missing from, or different on the printer.")
        msgbox.setDetailedText('\n'.join(missing))
        msgbox.exec_()

    def progressUpdater(self):
        QtCore.QTimer.singleShot(100, self.progressUpdater)
        if self.percent:
            self.progress.setValue(self.percent)
            if self.percent == 20:
                self.update()
            self.percent = None
        if self.labelText:
            self.progress.setLabelText(self.labelText)
            self.labelText = None
        if self.statusText:
            self.argentum.statusBar().showMessage(self.statusText)
            self.statusText = None
        if self.progress.wasCanceled() or self.printCanceled:
            if not self.printCanceled:
                self.argentum.printer.stop()
            if self.progress.wasCanceled():
                self.argentum.statusBar().showMessage("Print canceled.")
            self.printCanceled = True
            self.progress.hide()
        self.printPaused = self.progress.paused
        if self.missing:
            missing = self.missing
            self.missing = None
            self.reportMissing(missing)

    def fanAnimator(self):
        QtCore.QTimer.singleShot(1000 / self.fanSpeed, self.fanAnimator)
        if self.argentum.printer.leftFanOn or self.argentum.printer.rightFanOn:
            if self.fanImage == self.fanImage1:
                self.fanImage = self.fanImage2
            else:
                self.fanImage = self.fanImage1
            self.update()

    def printCross(self, x, y):
        pos = self.printAreaToMove(x, y)
        self.argentum.printer.move(pos[0], pos[1], wait=True)
        self.argentum.printer.Print("cross.hex", wait=True)

    def printCrossPattern(self, x, y):
        self.setProgress(labelText="Printing cross pattern...")
        self.printCross(x+ 0, y+ 0)
        self.setProgress(percent=20)
        self.printCross(x+10, y+ 0)
        self.setProgress(percent=40)
        self.printCross(x+20, y+ 0)
        self.setProgress(percent=60)
        self.printCross(x+10, y+10)
        self.setProgress(percent=80)
        self.printCross(x+10, y+20)
        self.setProgress(percent=100)

    def startPrint(self):
        if len(self.images) == 1:
            QtGui.QMessageBox.information(self,
                        "Nothing to print",
                        "You can add images to the print view by selecting\nFile -> Import Image or by simply dragging and dropping images onto the layout. All standard image file formats are supported, as well as industry standard Gerber files. You can also cut and paste from any graphics editing program.")

            return

        if self.printThread != None:
            print("Already printing!")
            return

        options = PrintOptionsDialog(self)
        if options.exec_() == options.Rejected:
            return

        self.printCanceled = False
        self.progress = PrintProgressDialog(self)
        self.progress.setWindowTitle("Printing")
        self.progress.setLabelText("Starting up...")
        self.progress.setValue(0)
        self.progress.show()

        self.printThread = threading.Thread(target=self.printLoop)
        self.printThread.passes = options.getPasses()
        self.printThread.useRollers = options.getUseRollers()
        self.printThread.dryingOnly = False
        self.printThread.start()

    def printLoop(self):
        try:
            self.setProgress(statusText="Printing.")

            processingStart = time.time()

            self.setProgress(labelText="Processing images...")
            self.perImage = 20.0 / (len(self.images) - 1)
            for image in self.images:
                if image == self.printHeadImage:
                    continue
                if not self.isImageProcessed(image):
                    self.setProgress(labelText="Processing image {}.".format(os.path.basename(image.filename)))
                    self.processImage(image)
                else:
                    self.setProgress(incPercent=self.perImage)

            processingEnd = time.time()
            self.argentum.addTimeSpentProcessingImages(processingEnd - processingStart)

            if not self.argentum.printer.connected:
                self.setProgress(labelText="Printer isn't connected.", statusText="Print aborted. Connect your printer.", canceled=True)
                return
            if (self.argentum.printer.version == None or
                    self.argentum.printer.majorVersion == 0 and
                    self.argentum.printer.minorVersion < 15):
                self.setProgress(labelText="Printer firmware too old.", statusText="Print aborted. Printer firmware needs upgrade.", canceled=True)
                return

            self.argentum.printer.turnLightsOn()

            # Now we can actually print!
            printingStart = time.time()
            for i in range(0, self.printThread.passes):
                self.setProgress(percent=20, labelText="Starting pass {}".format(i+1))
                self.argentum.printer.home(wait=True)
                self.perImage = 79.0 / (len(self.images) - 1)
                nImage = 0
                for image in self.images:
                    if image == self.printHeadImage:
                        continue
                    while self.progress.paused:
                        time.sleep(0.5)
                    pos = self.printAreaToMove(image.left + image.width, image.bottom)
                    self.argentum.printer.moveTo(pos[0], pos[1], withOk=True)
                    response = self.argentum.printer.waitForResponse(timeout=10, expect='Ok')
                    if response:
                        response = ''.join(response)
                        if response.find('/') != -1:
                            self.setProgress(statusText="Print error - ensure images are within print limits.", canceled=True)
                            return
                    self.setProgress(labelText="Pass {}: {}".format(i + 1, image.hexFilename))
                    path = os.path.join(self.argentum.filesDir, image.hexFilename)
                    while self.progress.paused:
                        time.sleep(0.5)
                    if not self.argentum.printer.send(path, progressFunc=self.sendProgress, printOnline=True):
                        self.setProgress(labelText="Printer error.", canceled=True)
                        return
                    nImage = nImage + 1
                    self.setProgress(percent=(20 + self.perImage * nImage))

                if self.printThread.useRollers:
                    self.dryingLoop()

            self.argentum.printer.home()
            self.setProgress(statusText='Print complete.', percent=100)
            printingEnd = time.time()
            self.argentum.addTimeSpentPrinting(printingEnd - printingStart)

        except PrintCanceledException:
            pass
        except:
            self.setProgress(statusText="Print error.", canceled=True)
            #raise
        finally:
            self.printThread = None
            self.argentum.printingCompleted = True

    def movePrintHead(self):
        xmm = self.printHeadImage.left - self.printHeadImage.minLeft
        ymm = self.printHeadImage.bottom - self.printHeadImage.minBottom
        self.argentum.printer.moveTo(xmm * 80, ymm * 80)

    def inTrashCan(self, image):
        if image == None:
            return False
        if image.screenRect == None:
            image.screenRect = self.printAreaToScreen(image)
        return self.trashCanRect.intersect(image.screenRect)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            if self.dragging == self.printHeadImage:
                self.movePrintHead()
            else:
                if self.inTrashCan(self.dragging):
                    self.images.remove(self.dragging)
                    self.layoutChanged = True
                else:
                    self.ensureImageInPrintLims(self.dragging)
                    self.dragging.screenRect = None
                    self.layoutChanged = True
        elif self.resizing:
            self.ensureImageInPrintLims(self.resizing)
            self.resizing.screenRect = None
            self.layoutChanged = True
        else:
            lights = False
            if self.leftLightsRect.contains(event.pos()):
                lights = True
            if self.rightLightsRect.contains(event.pos()):
                lights = True
            for light in self.bottomLightRects:
                if light.contains(event.pos()):
                    lights = True
            if lights:
                if self.argentum.printer.lightsOn:
                    self.argentum.printer.turnLightsOff()
                else:
                    self.argentum.printer.turnLightsOn()

            if self.leftFanRect.contains(event.pos()):
                if self.argentum.printer.leftFanOn:
                    self.argentum.printer.turnLeftFanOff()
                else:
                    self.argentum.printer.turnLeftFanOn()

            if self.rightFanRect.contains(event.pos()):
                if self.argentum.printer.rightFanOn:
                    self.argentum.printer.turnRightFanOff()
                else:
                    self.argentum.printer.turnRightFanOn()

            kerf = False
            if self.leftKerfRect.contains(event.pos()):
                kerf = True
            if self.rightKerfRect.contains(event.pos()):
                kerf = True
            if kerf:
                if self.colorPicker.isVisible():
                    self.colorPicker.hide()
                else:
                    self.colorPicker.show()

        if self.dragging and self.dragging != self.printHeadImage:
            self.selection = self.dragging
        elif self.resizing:
            self.selection = self.resizing

        self.dragging = None
        self.resizing = None
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.update()

    def colorPicked(self, color):
        self.argentum.printer.command("red {}".format(color.red()))
        self.argentum.printer.command("green {}".format(color.green()))
        self.argentum.printer.command("blue {}".format(color.blue()))
        self.kerfPen.setColor(color)
        self.update()

    def ensureImageInPrintLims(self, image):
        if image == self.printHeadImage:
            if image.left < image.minLeft:
                image.left = image.minLeft
            if image.bottom < image.minBottom:
                image.left = image.minBottom
            return

        if image.left < self.printLims.left:
            image.left = self.printLims.left
        if image.bottom < self.printLims.bottom:
            image.bottom = self.printLims.bottom
        if image.left + image.width > self.printLims.left + self.printLims.width:
            image.left = (self.printLims.left +
                            self.printLims.width - image.width)
        if image.bottom + image.height > self.printLims.bottom + self.printLims.height:
            image.bottom = (self.printLims.bottom +
                                self.printLims.height - image.height)

        if image.left < self.printLims.left:
            image.left = self.printLims.left
            image.width = self.printLims.width
        if image.bottom < self.printLims.bottom:
            image.bottom = self.printLims.bottom
            image.height = self.printLims.height

    def mouseMoveEvent(self, event):
        pressed = event.buttons() & QtCore.Qt.LeftButton
        p = self.screenToPrintArea(event.pos().x(), event.pos().y())
        if p == None:
            if self.dragging == None and self.resizing == None:
                self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return

        self.showTrashCanOpen = self.inTrashCan(self.dragging)

        px = p[0]
        py = p[1]
        #print("{}, {}".format(px, py))

        if pressed and self.dragging != None:
            image = self.dragging
            image.left = px - self.dragStart[0] + self.dragImageStart[0]
            image.bottom = py - self.dragStart[1] + self.dragImageStart[1]
            image.screenRect = None
            self.layoutChanged = True
            self.update()
        elif pressed and self.resizing != None:
            image = self.resizing
            (leftEdge, rightEdge, topEdge, bottomEdge) = self.resizeEdges
            (startLeft, startBottom, startWidth, startHeight) = self.resizeImageStart
            dx = px - self.resizeStart[0]
            dy = py - self.resizeStart[1]
            if leftEdge:
                if dx + startLeft < startLeft + startWidth:
                    image.left = dx + startLeft
                    image.width = startWidth + startLeft - image.left
            elif rightEdge:
                if dx + startWidth > 0:
                    image.width = dx + startWidth

            if topEdge:
                if dy + startHeight > 0:
                    image.height = dy + startHeight
            elif bottomEdge:
                if dy + startBottom < startBottom + startHeight:
                    image.bottom = dy + startBottom
                    image.height = startHeight + startBottom - image.bottom

            image.lastResized = time.time()
            image.screenRect = None
            self.layoutChanged = True
            self.update()
        elif self.dragging == None and self.resizing == None:
            hit = False
            for image in self.images:
                if image == self.printHeadImage and not self.showingPrintHead:
                    continue
                leftEdge = False
                rightEdge = False
                topEdge = False
                bottomEdge = False
                n = 1.1 if pressed else 1.0
                if (py >= image.bottom - n and
                        py < image.bottom + image.height + n):
                    if px >= image.left - n and px <= image.left:
                        leftEdge = True
                    if (px < image.left + image.width + n and
                            px >= image.left + image.width):
                        rightEdge = True
                if (px >= image.left - n and
                        px < image.left + image.width + n):
                    if py >= image.bottom - n and py <= image.bottom:
                        bottomEdge = True
                    if (py < image.bottom + image.height + n and
                            py >= image.bottom + image.height):
                        topEdge = True

                anyEdge = True
                if leftEdge and bottomEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeBDiagCursor))
                elif rightEdge and topEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeBDiagCursor))
                elif leftEdge and topEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
                elif rightEdge and bottomEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
                elif leftEdge or rightEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeHorCursor))
                elif topEdge or bottomEdge:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.SizeVerCursor))
                else:
                    anyEdge = False

                if image == self.printHeadImage:
                    anyEdge = False

                if anyEdge:
                    hit = True
                    if pressed:
                        self.resizing = image
                        self.resizeImageStart = (image.left, image.bottom, image.width, image.height)
                        self.resizeStart = (px, py)
                        self.resizeEdges = (leftEdge, rightEdge, topEdge, bottomEdge)
                    break

                if px >= image.left and px < image.left + image.width:
                    if py >= image.bottom and py < image.bottom + image.height:
                        hit = True
                        if pressed:
                            self.dragging = image
                            self.dragImageStart = (image.left, image.bottom)
                            self.dragStart = (px, py)
                            self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
                        else:
                            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
                        break

            if not hit:
                self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def dragEnterEvent(self, e):
        self.argentum.raise_()
        self.argentum.activateWindow()
        e.accept()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            url = str(e.mimeData().urls()[0].path())
            pi = self.addDroppedFile(url, e.pos())
            if pi:
                self.selection = pi

    def addDroppedFile(self, path, pos=None):
        if path[0] == '/' and path[2] == ':':
            # Windows
            path = path[1:]
        if path[-7:] == ".layout":
            self.openLayout(path)
            return None
        pi = self.addImageFile(path)
        if pi == None:
            return None
        if pos:
            p = self.screenToPrintArea(pos.x(), pos.y())
        else:
            p = (self.printLims.left + self.printLims.width / 2,
                 self.printLims.bottom + self.printLims.height / 2)
        if p != None:
            pi.left = p[0] - pi.width / 2
            pi.bottom = p[1] - pi.height / 2
            self.ensureImageInPrintLims(pi)
        return pi

    def copy(self):
        if self.selection == None:
            print("nothing to copy")
            return
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setPixmap(self.selection.pixmap)

    def cut(self):
        if self.selection == None:
            print("nothing to cut")
            return
        self.copy()
        self.images.remove(self.selection)
        self.layoutChanged = True
        self.update()

    def delete(self):
        if self.selection == None:
            print("nothing to delete")
            return
        self.images.remove(self.selection)
        self.layoutChanged = True
        self.update()

    def paste(self):
        clipboard = QtGui.QApplication.clipboard()
        if clipboard.mimeData().hasUrls():
            url = str(clipboard.mimeData().urls()[0].path())
            pi = self.addDroppedFile(url)
            if pi != None:
                self.selection = pi
            return

        if clipboard.mimeData().hasImage():
            image = clipboard.mimeData().imageData().toPyObject()
            fname = tempfile.mktemp() + ".png"
            print("using temp file " + fname)
            image.save(fname);
            pi = self.addDroppedFile(fname)
            if pi != None:
                self.selection = pi
            return

    def crop(self):
        if self.selection == None:
            print("nothing to crop")
            return

        image = self.selection.pixmap.toImage()

        nTop = 0
        for j in range(0, image.height()):
            rowIsEmpty = True
            for i in range(0, image.width()):
                blue = QtGui.qBlue(image.pixel(i, j))
                if blue <= 200:
                    rowIsEmpty = False
                    break
            if rowIsEmpty:
                nTop = nTop + 1
            else:
                break

        nWidth = image.width()
        for i in range(0, image.width()):
            colIsEmpty = True
            for j in range(0, image.height()):
                blue = QtGui.qBlue(image.pixel(image.width() - i - 1, j))
                if blue <= 200:
                    colIsEmpty = False
                    break
            if colIsEmpty:
                nWidth = nWidth - 1
            else:
                break

        nLeft = 0
        for i in range(0, image.width()):
            colIsEmpty = True
            for j in range(0, image.height()):
                blue = QtGui.qBlue(image.pixel(i, j))
                if blue <= 200:
                    colIsEmpty = False
                    break
            if colIsEmpty:
                nLeft = nLeft + 1
            else:
                break

        nHeight = image.height()
        for j in range(0, image.height()):
            rowIsEmpty = True
            for i in range(0, image.width()):
                blue = QtGui.qBlue(image.pixel(i, image.height() - j - 1))
                if blue <= 200:
                    rowIsEmpty = False
                    break
            if rowIsEmpty:
                nHeight = nHeight - 1
            else:
                break

        nBottom = image.height() - nHeight
        image = image.copy(nLeft, nTop, nWidth - nLeft, nHeight - nTop)
        fname = tempfile.mktemp() + ".png"
        print("using temp file " + fname)
        image.save(fname);

        self.images.remove(self.selection)
        newImage = self.addImageFile(fname)
        newImage.left = self.selection.left + nLeft / imageScale[0]
        newImage.bottom = self.selection.bottom + nBottom / imageScale[1]
        newImage.screenRect = None
        self.layoutChanged = True
        self.update()

    def openLayout(self, filename=None):
        if self.closeLayout() == False:
            return

        if filename == None:
            filename = str(QtGui.QFileDialog.getOpenFileName(self, 'Select a layout', self.argentum.filesDir, "Layouts (*.layout)"))
        if filename == None:
            return

        file = open(filename, "r")
        lines = file.read().split('\n')
        file.close()

        layoutPath = os.path.dirname(filename)
        bImageSection = False
        image = None
        for line in lines:
            if len(line) == 0:
                continue
            if line[0] == '#':
                continue
            if line[0] == '[':
                bImageSection = False
                if line == '[image]':
                    bImageSection = True
                continue
            if line.find('=') == -1:
                # What is this?
                continue

            key = line[0:line.find('=')]
            value = line[line.find('=')+1:]

            if bImageSection:
                if key == "filename":
                    if image:
                        self.ensureImageInPrintLims(image)
                    filename = value
                    if not os.path.isabs(filename):
                        filename = os.path.join(layoutPath, filename)
                    image = self.addImageFile(filename)
                if image:
                    if key == "left":
                        image.left = float(value)
                    if key == "bottom":
                        image.bottom = float(value)
                    if key == "width":
                        image.width = float(value)
                    if key == "height":
                        image.height = float(value)
                    if key == "lastResized":
                        image.lastResized = float(value)
        if image:
            self.ensureImageInPrintLims(image)

        self.layout = filename
        self.update()

    def saveLayout(self, filename=None):
        if self.layout == None:
            if filename == None:
                filename = str(QtGui.QFileDialog.getSaveFileName(self, 'Save layout as', self.argentum.filesDir, "Layouts (*.layout)"))
                if filename == None:
                    return
                if filename.find('.layout') != len(filename)-7:
                    filename = filename + '.layout'
        else:
            filename = self.layout

        # TODO we really need to create an archive of the control file
        #      and all the images used
        #
        # XXX Saves full pathnames. :(
        file = open(filename, "w")
        layoutPath = os.path.dirname(filename)
        for image in self.images:
            if image == self.printHeadImage:
                continue
            file.write('[image]\n')
            path = os.path.relpath(image.filename, layoutPath)
            if path.find('..') != -1:
                path = image.filename
            file.write('filename={}\n'.format(path))
            file.write('left={}\n'.format(image.left))
            file.write('bottom={}\n'.format(image.bottom))
            file.write('width={}\n'.format(image.width))
            file.write('height={}\n'.format(image.height))
            if image.lastResized:
                file.write('lastResized={}\n'.format(image.lastResized))
            file.write('\n')
        file.close()

        self.layout = filename
        self.layoutChanged = False
        self.update()
        return True

    def closeLayout(self):
        if len(self.images) == 1:
            self.layout = None
            self.layoutChanged = False
            self.update()
            return True

        if self.layoutChanged:
            answer = QtGui.QMessageBox.question(self, "Unsaved Changes",
                "Would you like to save the current layout?",
                (QtGui.QMessageBox.Save |
                 QtGui.QMessageBox.Discard |
                 QtGui.QMessageBox.Cancel))
            if answer == QtGui.QMessageBox.Save:
                if not self.saveLayout():
                    return False
            elif answer == QtGui.QMessageBox.Cancel:
                return False

        self.images = [self.printHeadImage]
        self.layout = None
        self.layoutChanged = False
        self.update()

        return True
