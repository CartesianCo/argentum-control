#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
from imageproc import ImageProcessor

if len(sys.argv) > 1:
    ip = ImageProcessor()

    inputFileName = sys.argv[1]

    dotPosition = inputFileName.rfind('.')

    if dotPosition <= 0:
        dotPosition = len(inputFileName)

    outputFileName = inputFileName[:dotPosition] + '.argentum'

    ip.sliceImage(inputFileName, outputFileName)
else:
    print('usage: {} <filename>'.format(sys.argv[0]))
