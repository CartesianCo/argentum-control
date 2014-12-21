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

printPlateDesignScale = [1.0757, 1.2256] # * printArea
imageScale            = [ 23.70,  23.70] # * print = pixels

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

class PrintView(QtGui.QWidget):
    layout = None
    layoutChanged = False
    printThread = None
    dragging = None
    resizing = None

    def __init__(self, argentum):
        super(PrintView, self).__init__()
        self.argentum = argentum
        self.lastRect = QtCore.QRect()
        self.progress = QtGui.QProgressDialog(self)
        self.progress.setWindowTitle("Printing")
        QtCore.QTimer.singleShot(100, self.progressUpdater)

        self.printPlateArea = PrintRect(0, 0, 285, 255)
        self.printArea = PrintRect(24, 73, 247, 127)
        self.printLims = PrintRect(10, 0, 230, 120)
        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")
        self.trashCan         = QtSvg.QSvgRenderer("trashCan.svg")
        height = self.printArea.height * printPlateDesignScale[1]
        self.printPlateDesignArea = PrintRect(12,
                    50,
                    self.printArea.width * printPlateDesignScale[0],
                    height)
        self.images = []
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
        self.trashCanRect = QtCore.QRectF(
           (self.printPlateDesignRect.left() +
            self.printPlateDesignRect.width() * 19 / 21),
           (self.printPlateDesignRect.top() +
            self.printPlateDesignRect.height() * 5 / 7),
           self.printPlateDesignRect.width() / 7,
           self.printPlateDesignRect.height() / 5)

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
        fudgeX = 3
        fudgeY = 6
        x = offsetX * moveScale[0] - fudgeX * moveScale[0]
        y = offsetY * moveScale[1] - fudgeY * moveScale[1]
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
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp, self.printPlateDesignRect)
        if self.dragging:
            self.trashCan.render(qp, self.trashCanRect)
        for image in self.images:
            qp.drawPixmap(image.screenRect, image.pixmap, image.pixmapRect())
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
        imgModified = os.path.getmtime(image.filename)
        hexModified = os.path.getmtime(hexFilename)
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
        if self.printCanceled:
            return False
        self.setProgress(percent=(20 + self.perImage * pos / size))
        return True

    def printProgress(self, pos, size):
        if self.printCanceled:
            return False
        self.setProgress(percent=(40 + self.perImage * pos / size))
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
                image.hexFilename = "{}-{}x{}.hex".format(
                                    image.hexFilename[:-4], size[0], size[1])
                hexFilename = os.path.join(self.argentum.filesDir,
                                           image.hexFilename)
                self.layoutChanged = True

            ip.sliceImage(image.pixmap.toImage(), hexFilename,
                            progressFunc=self.imageProgress,
                            size=size)
        except:
            print("error processing {}.".format(image.filename))
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
        self.progress = QtGui.QProgressDialog(self)
        self.progress.setWindowTitle("Printing")
        self.progress.setLabelText("Starting up...")
        self.progress.setValue(0)
        self.progress.show()

        self.printThread = threading.Thread(target=self.printLoop)
        self.printThread.start()

    def printLoop(self):
        try:
            self.setProgress(statusText="Printing.")

            self.setProgress(labelText="Processing images...")
            self.perImage = 20.0 / len(self.images)
            for image in self.images:
                if not self.isImageProcessed(image):
                    self.setProgress(labelText="Processing image {}.".format(os.path.basename(image.filename)))
                    self.processImage(image)
                else:
                    self.setProgress(incPercent=self.perImage)

            if not self.argentum.printer.connected:
                self.setProgress(labelText="Printer isn't connected.", statusText="Print aborted. Connect your printer.", canceled=True)
                return
            if (self.argentum.printer.version == None or
                    self.argentum.printer.majorVersion == 0 and
                    self.argentum.printer.minorVersion < 15):
                self.setProgress(labelText="Printer firmware too old.", statusText="Print aborted. Printer firmware needs upgrade.", canceled=True)
                return

            self.setProgress(labelText="Looking on the printer...")
            hexfiles = [image.hexFilename for image in self.images]
            missing = self.argentum.printer.missingFiles(hexfiles)
            print("{} missing files.".format(len(missing)))

            # Try harder
            if len(missing) != 0:
                self.setProgress(labelText="Looking on the printer for {} missing files...".format(len(missing)))
                self.argentum.printer.disconnect()
                self.argentum.printer.connect()
                missing = self.argentum.printer.missingFiles(hexfiles)
                print("{} still missing files.".format(len(missing)))

            # Also check the files we did find to see if they're different
            for filename in hexfiles:
                if filename in missing:
                    continue
                path = os.path.join(self.argentum.filesDir, filename)
                if not self.argentum.printer.checkDJB2(path):
                    missing.append(filename)
                    print("{} is different.".format(filename))

            # Try sending missing files
            if len(missing) != 0:
                self.setProgress(percent=20)
                self.perImage = 20.0 / len(missing)
            sent = []
            for filename in missing:
                self.setProgress(labelText="Sending {}...".format(filename))
                path = os.path.join(self.argentum.filesDir, filename)
                self.argentum.printer.send(path, progressFunc=self.sendProgress)
                if self.argentum.printer.checkDJB2(path):
                    sent.append(filename)
            for filename in sent:
                missing.remove(filename)

            # Nope, and this is fatal
            if len(missing) != 0:
                self.setProgress(missing=missing, statusText="Print aborted.")
                return

            # Now we can actually print!
            self.setProgress(percent=40, labelText="Printing...")
            self.argentum.printer.disconnect()
            self.argentum.printer.connect()
            self.perImage = 59.0 / len(self.images)
            nImage = 0
            for image in self.images:
                pos = self.printAreaToMove(image.left + image.width, image.bottom)
                self.argentum.printer.home(wait=True)
                self.argentum.printer.move(pos[0], pos[1])
                path = os.path.join(self.argentum.filesDir, image.hexFilename)
                self.setProgress(labelText=image.hexFilename)
                self.argentum.printer.Print(image.hexFilename,
                                            path=path,
                                            progressFunc=self.printProgress)
                nImage = nImage + 1
                self.setProgress(percent=(40 + self.perImage * nImage))

            self.setProgress(statusText='Print complete.', percent=100)
        except PrintCanceledException:
            pass
        except:
            self.setProgress(statusText="Print error.", canceled=True)
            raise
        finally:
            self.printThread = None

    def mouseReleaseEvent(self, event):
        if self.dragging:
            screenRect = self.printAreaToScreen(self.dragging)
            if (event.pos().x() > self.trashCanRect.left() and
                    event.pos().y() > self.trashCanRect.top()):
                self.images.remove(self.dragging)
                self.layoutChanged = True

        self.dragging = None
        self.resizing = None
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.update()

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
            if self.dragging == None and self.resizing == None:
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

            self.ensureImageInPrintLims(image)
            image.lastResized = time.time()
            image.screenRect = None
            self.layoutChanged = True
            self.update()
        elif self.dragging == None and self.resizing == None:
            hit = False
            for image in self.images:
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
            if url[0] == '/' and url[2] == ':':
                # Windows
                url = url[1:]
            if url[-7:] == ".layout":
                self.openLayout(url)
                return
            pi = self.addImageFile(url)
            if pi == None:
                return
            p = self.screenToPrintArea(e.pos().x(), e.pos().y())
            if p != None:
                pi.left = p[0] - pi.width / 2
                pi.bottom = p[1] - pi.height / 2
                self.ensureImageInPrintLims(pi)

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
        if len(self.images) == 0:
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

        self.images = []
        self.layout = None
        self.layoutChanged = False
        self.update()

        return True
