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
from PIL import Image, ImageDraw

def compare_images(filename1, filename2):
    image1 = Image.open(filename1)
    image2 = Image.open(filename2)

    mat1 = image1.load()
    mat2 = image2.load()

    if image1.size != image2.size:
        print('Sizes differ')
        return -1

    width, height = image1.size

    for y in xrange(height):
        for x in xrange(width):
            pos = (x, y)

            if mat1[pos] != mat2[pos]:
                print('Pixels differ at {}'.format(pos))

    print('Images are identical.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: {} <image 1> <image 2>'.format(sys.argv[0]))
        sys.exit(-1)

    sys.exit(compare_images(sys.argv[1], sys.argv[2]))
