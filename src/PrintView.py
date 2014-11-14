#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control PrintView

author: Trent Waddington
"""

import sys
import os
import threading
from PyQt4 import QtGui, QtCore, QtSvg

printPlateDesignScale = [1.0757, 1.2256] # * printArea
imageScale            = [ 23.52,  23.29] # * print = pixels

# moves / mm
moveScale             = [3000 / 37, 3000 / 39]

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
        self.screenRect = None

        filename = os.path.basename(filename)
        if filename.find('.') != -1:
            filename = filename[:filename.find('.')]
        self.hexFilename = filename + ".hex"

    def pixmapRect(self):
        return QtCore.QRectF(self.pixmap.rect())

class PrintView(QtGui.QWidget):
    def __init__(self, argentum):
        super(PrintView, self).__init__()
        self.argentum = argentum
        self.lastRect = QtCore.QRect()
        self.printThread = None
        self.progress = QtGui.QProgressDialog(self)
        self.progress.setWindowTitle("Printing")
        QtCore.QTimer.singleShot(100, self.progressUpdater)

        self.printPlateArea = PrintRect(0, 0, 285, 255)
        self.printArea = PrintRect(24, 73, 247, 127)
        self.printLims = PrintRect(10, 0, 230, 120)
        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")
        height = self.printArea.height * printPlateDesignScale[1]
        self.printPlateDesignArea = PrintRect(12, 
                    50,
                    self.printArea.width * printPlateDesignScale[0],
                    height)
        self.images = []
        self.dragging = None
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

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
        x = offsetX * moveScale[0]
        y = offsetY * moveScale[1]
        x = int(x)
        y = int(y)
        return (x, y)

    def screenToPrintArea(self, x, y):
        r = self.printToScreen(self.printArea)
        if x < r.left():
            x = r.left()
        if x > r.left() + r.width():
            x = r.left() + r.width()
        if y < r.top():
            y = r.top()
        if y > r.top() + r.height():
            y = r.top() + r.height()

        dx = x - r.left()
        dy = y - r.top()

        return (dx * self.printArea.width / r.width(),
                self.printArea.height - dy * self.printArea.height / r.height())

    def paintEvent(self, event):
        self.calcScreenRects()

        qp = QtGui.QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp, self.printPlateDesignRect)
        for image in self.images:
            qp.drawPixmap(image.screenRect, image.pixmap, image.pixmapRect())
        qp.end()

    def addImageFile(self, inputFileName):
        pixmap = QtGui.QPixmap(inputFileName)
        if pixmap.isNull():
            print("Can't load image " + inputFileName)
            return None
        pi = PrintImage(pixmap, inputFileName)
        self.images.append(pi)
        self.ensureImageInPrintLims(pi)
        self.update()
        return pi

    def isImageProcessed(self, image):
        hexFilename = os.path.join(self.argentum.filesDir, image.hexFilename)
        if not os.path.exists(hexFilename):
            return False
        if os.path.getsize(hexFilename) == 0:
            return False
        imgModified = os.path.getmtime(image.filename)
        hexModified = os.path.getmtime(hexFilename)
        if imgModified < hexModified:
            return True
        return False

    def processImage(self, image):
        ip = self.argentum.getImageProcessor()
        hexFilename = os.path.join(self.argentum.filesDir, image.hexFilename)
        print("processing " + image.filename)
        try:
            ip.sliceImage(image.filename, hexFilename)
        except:
            print("error processing {}.".format(image.filename))
            self.setProgress(labelText="Error processing {}.".format(image.filename))
            print("removing {}.".format(hexFilename))
            os.remove(hexFilename)
            raise

    percent = None
    labelText = None
    statusText = None
    missing = None
    printCanceled = False
    def setProgress(self, percent=None,
                          incPercent=None,
                          labelText=None,
                          statusText=None,
                          missing=None,
                          canceled=None):
        if self.printCanceled:
            raise Exception()
        if percent:
            self.percent = percent
        if incPercent:
            if self.percent == None:
                self.percent = 0
            self.percent = self.percent + incPercent
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
        msgbox.setText("One or more files are missing from the printer.")
        msgbox.setDetailedText('\n'.join(missing))
        msgbox.exec_()

    def progressUpdater(self):
        QtCore.QTimer.singleShot(100, self.progressUpdater)
        if self.percent:
            self.progress.setValue(self.percent)
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
            self.printCanceled = True
            self.progress.hide()
        if self.missing:
            missing = self.missing
            self.missing = None
            self.reportMissing(missing)

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
        if len(self.images) == 0:
            self.argentum.statusBar().showMessage('Add some images to print.')
            return

        if self.printThread != None:
            print("Already printing!")
            return

        self.printCanceled = False
        self.progress.setLabelText("Starting up...")
        self.progress.setValue(0)
        self.progress.show()

        self.printThread = threading.Thread(target=self.printLoop)
        self.printThread.start()

    def printLoop(self):
        try:
            #self.printCrossPattern(30, 30)
            #return

            self.setProgress(labelText="Processing images...")
            perImage = 40 / len(self.images)
            for image in self.images:
                if not self.isImageProcessed(image):
                    self.setProgress(labelText="Processing image {}.".format(os.path.basename(image.filename)))
                    self.processImage(image)
                self.setProgress(incPercent=perImage)

            if not self.argentum.printer.connected:
                self.setProgress(labelText="Printer isn't connected.", statusText="Print aborted.", canceled=True)
                return


            self.setProgress(labelText="Looking on the printer...")
            hexfiles = [image.hexFilename for image in self.images]
            missing = self.argentum.printer.missingFiles(hexfiles)

            # Try harder
            if len(missing) != 0:
                self.setProgress(labelText="Looking on the printer for {} missing files...".format(len(missing)))
                self.argentum.printer.disconnect()
                self.argentum.printer.connect(wait=True)
                missing = self.argentum.printer.missingFiles(hexfiles)

            # Nope, and this is fatal
            if len(missing) != 0:
                self.setProgress(missing=missing, statusText="Print aborted.")
                return

            self.setProgress(percent=40, labelText="Printing...")
            perImage = 59 / len(self.images)
            for image in self.images:
                pos = self.printAreaToMove(image.left + image.width, image.bottom)
                self.argentum.printer.home(wait=True)
                self.argentum.printer.move(pos[0], pos[1], wait=True)
                self.argentum.printer.Print(image.hexFilename, wait=True)
                self.setProgress(incPercent=perImage)

            self.setProgress(statusText='Print complete.', percent=100)
        except:
            self.setProgress(statusText="Print canceled.", canceled=True)
            raise
        finally:
            self.printThread = None

    def mouseReleaseEvent(self, event):
        self.dragging = None
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def ensureImageInPrintLims(self, image):
        if image.left < self.printLims.left:
            image.left = self.printLims.left
        if image.bottom < self.printLims.bottom:
            image.bottom = self.printLims.bottom
        if image.left + image.width > self.printLims.width:
            image.left = (self.printLims.left +
                            self.printLims.width - image.width)
        if image.bottom + image.height > self.printLims.height:
            image.bottom = (self.printLims.bottom +
                                self.printLims.height - image.height)

    def mouseMoveEvent(self, event):
        pressed = event.buttons() & QtCore.Qt.LeftButton
        p = self.screenToPrintArea(event.pos().x(), event.pos().y())
        if p == None:
            if self.dragging == None:
                self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return

        px = p[0]
        py = p[1]
        #print("{}, {}".format(px, py))

        if pressed and self.dragging != None:
            image = self.dragging
            image.left = px - self.dragStart[0] + self.dragImageStart[0]
            image.bottom = py - self.dragStart[1] + self.dragImageStart[1]
            self.ensureImageInPrintLims(image)
            image.screenRect = None
            self.update()
        elif self.dragging == None:
            hit = False
            for image in self.images:
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
            if url[0] == '/' and url[2] == ':':
                # Windows
                url = url[1:]
            pi = self.addImageFile(url)
            if pi == None:
                return
            p = self.screenToPrintArea(e.pos().x(), e.pos().y())
            if p != None:
                pi.left = p[0] - pi.width / 2
                pi.bottom = p[1] - pi.height / 2
                self.ensureImageInPrintLims(pi)
