#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Argentum Control PrintView

author: Trent Waddington
"""

import sys
import os
from PyQt4 import QtGui, QtCore

class PrintView(QtGui.QWidget):
    def __init__(self, argentum):
        super(PrintView, self).__init__()

        self.argentum = argentum

