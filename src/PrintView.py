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
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height

class PrintImage:
    def __init__(self, pixmap):
        self.pixmap = pixmap
        self.left = 0
        self.bottom = 0

class PrintView(QtGui.QWidget):
    def __init__(self):
        super(PrintView, self).__init__()

        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")
        self.images = []

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp)
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
