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

class PrintView(QtGui.QWidget):
    def __init__(self):
        super(PrintView, self).__init__()

        self.printPlateDesign = QtSvg.QSvgRenderer("printPlateDesign.svg")

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QtGui.QColor(0,0,0))
        self.printPlateDesign.render(qp)
        qp.end();

