#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington
    Copyright (C) 2015 Michael Reed

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

# Hash define equivalents for passing a value
X_AXIS = 0
Y_AXIS = 1

class argentum_v1_2():

    def writeMoveCmd(self, cartridgeAxis, steps, outputStream):
        if cartridgeAxis == X_AXIS:
            printerAxis = 'Y'
            steps *= -1
        else:
            printerAxis = 'X'
        outputStream.write('M {} {}\n'.format(axis, steps).encode('utf-8'))
