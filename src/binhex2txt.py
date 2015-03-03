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

import sys
import os

def bin2txt(filename):
    f = open(filename, "r")
    contents = f.read()
    f.close()

    i = 0
    while i < len(contents):
        if contents[i] == 'M':
            while contents[i] != '\n':
                sys.stdout.write(contents[i])
                i = i + 1
            sys.stdout.write('\n')
        elif contents[i] == chr(1):
            i = i + 1
            firing1 = ord(contents[i])
            i = i + 1
            address1 = ord(contents[i])
            i = i + 1
            if contents[i] != '\n' and contents[i] != chr(0):
                sys.stderr.write("Invalid firing command.\n")
                sys.exit(1)
            i = i + 1
            if contents[i] != chr(1):
                sys.stderr.write("Invalid firing command.\n")
                sys.exit(1)
            i = i + 1
            firing2 = ord(contents[i])
            i = i + 1
            address2 = ord(contents[i])
            i = i + 1
            if address1 != address2:
                sys.stderr.write("Invalid firing command.\n")
                sys.exit(1)
            sys.stdout.write('F {:01X}{:02X}{:02X}\n'.format(address1, firing1, firing2).encode('utf-8'))
        else:
            sys.stderr.write("Invalid hex file.\n")
            sys.exit(1)
        i = i + 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: binhex2txt.py <binary hex file>")
        sys.exit(1)

    bin2txt(sys.argv[1])
    sys.exit(0)
