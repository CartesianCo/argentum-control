#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control PrintView

author: Trent Waddington
"""

import sys
import os
from PyQt4 import QtGui, QtCore, QtSvg

# A kind of annoying Rect
# Note: (0,0) is the bottom left corner of the printer
# All measurements are in millimeters
class PrintRect:
    def __init__(self, left, bottom, width, height):
        self.left   = float(left)
        self.bottom = float(bottom)
        self.width  = float(width)
        self.height = float(height)

class PrintImage:
    def __init__(self, pixmap):
        self.pixmap = pixmap
        self.left = 0
        self.bottom = 0

class PrintView(QtGui.QWidget):
    def __init__(self):
        super(PrintView, self).__init__()

        self.printPlateArea = PrintRect(0, 0, 285, 255)
        self.printArea = PrintRect(24, 73, 247, 127)
        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")
        self.printPlateDesignScale = [1.0757, 1.2256] # * printArea
        self.printPlateDesignArea = PrintRect(0, 0, 
                        self.printArea.width * self.printPlateDesignScale[0],
                        self.printArea.height * self.printPlateDesignScale[1])
        self.images = []

    def calcPrintPlateDesignRect(self):
        # Ensure correct aspect ratio
        aspectRect = QtCore.QRectF(self.rect())
        aspectRatio = aspectRect.width() / aspectRect.height()
        desiredAspectRatio = self.printArea.width / self.printArea.height
        #print("window {}x{}".format(aspectRect.width(), aspectRect.height()))
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

        return aspectRect

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp, self.calcPrintPlateDesignRect())

        for image in self.images:
            qp.drawPixmap(QtCore.QPointF(image.left, 
                                  self.rect().height() - image.bottom - image.pixmap.height()),
                          image.pixmap)

        qp.end();

    def addImageFile(self, inputFileName):
        pixmap = QtGui.QPixmap(inputFileName)
        if not pixmap:
            print("Can't load image " + inputFileName)
            return
        self.images.append(PrintImage(pixmap))
