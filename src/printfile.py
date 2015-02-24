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
import io

class PrintFile:
    file = None
    fileName = None
    fileSize = 0

    def __init__(self, fileName, commandHandler=None):
        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

        self.fileSize = self.file.seek(0, io.SEEK_END)
        self.rewind()

    def rewind(self):
        self.file.seek(0, io.SEEK_SET)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        packet = self.nextCommand()

        if packet:
            return packet
        else:
            raise StopIteration

    def nextCommand(self):
        byte = self.file.read(1)

        if not byte:
            return None

        opcode = ord(byte[0])

        if opcode == 1:
            firing_data = self.file.read(7)

            primitive1 = ord(firing_data[0])
            address1 = ord(firing_data[1])
            primitive2 = ord(firing_data[4])
            address2 = ord(firing_data[5])

            ret = (
                'firing',
                [[primitive1, address1], [primitive2, address2]]
            )

            return ret

        if opcode == ord('M'):
            movement_data = self.file.readline()

            movement_data = movement_data.split()

            axis = movement_data[0]
            steps = movement_data[1]

            ret = (
                'move',
                [{axis: steps}]
            )

            return ret

        print('Unknown Code: {}'.format(opcode))
        return None
