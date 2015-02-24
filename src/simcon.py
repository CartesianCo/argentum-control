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

from controllers import ParsingControllerBase
from CartesianCo import ArgentumEmulator

class SimulatorController(ParsingControllerBase):
    def __init__(self):
        self.printer = ArgentumEmulator(None, None)

    def incrementalMovementCommand(self, axis, steps):
        print(self.printer.currentPosition)
        #print('incrementalMovementCommand on {} axis for {} steps.'.format(axis, steps))
        if axis == 'X':
            if steps == 0:
                self.printer.moveToX(0)
            else:
                self.printer.incrementX(xIncrement=steps)

        if axis == 'Y':
            if steps == 0:
                self.printer.moveToY(0)
            else:
                self.printer.incrementY(yIncrement=steps)

    def firingCommand(self, primitives1, address1, primitives2, address2):
        print('firingCommand on primitives {}-{} and address {}.'.format(primitives1, primitives2, address1))
        pass
