#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control PrintView

author: Trent Waddington
"""

import sys
import os
from PyQt4 import QtGui, QtCore, Qt

# A kind of annoying Rect
# Note: (0,0) is the bottom left corner of the printer
# All measurements are in millimeters
class PrintRect:
    def __init__(self, left, bottom, width, height):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height

class PrintView(QtGui.QWidget):
    def __init__(self):
        super(PrintView, self).__init__()

        self.logo = QtGui.QPixmap("cartesianco_logo.png")

        self.totalArea = PrintRect( 0.0,   0.0, 285.0, 256.0)
        self.logoArea  = PrintRect(19.0,  56.0,  68.0,  17.0)
        self.printArea = PrintRect(24.0,  75.0, 246.0, 128.0)

    def paintEvent(self, event):

        width = self.totalArea.left + self.totalArea.width
        height = self.totalArea.bottom + self.totalArea.height
        scale = [self.rect().width() / width,
                 self.rect().height() / height]

        qp = QtGui.QPainter()
        qp.begin(self)
        qp.scale(scale[0], scale[1])
        qp.fillRect(QtCore.QRectF(0, 0, width, height), 
                    QtGui.QColor(0,0,0))
    
        qp.fillRect(QtCore.QRectF(self.printArea.left, 
                                  height - self.printArea.bottom - self.printArea.height, 
                                  self.printArea.width, 
                                  self.printArea.height), 
                    QtGui.QColor(10,10,10))

        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1, QtCore.Qt.SolidLine))

        crossSpacing = 20
        for y in range(0, 7):
            for x in range(0, 13):
                left = self.printArea.left + x * crossSpacing
                bottom = height - self.printArea.bottom - y * crossSpacing
                qp.drawLine(left, bottom - 3.5, left + 6, bottom - 3.5)
                qp.drawLine(left + 3.5, bottom - 7, left + 3.5, bottom)

        # draw the logo
        qp.translate(self.logoArea.left, 
                     height - self.logoArea.bottom - self.logoArea.height)
        qp.scale(self.logoArea.width / self.logo.width(),
                 self.logoArea.height / self.logo.height())
        qp.drawPixmap(0, 0, self.logo)
        qp.end()

