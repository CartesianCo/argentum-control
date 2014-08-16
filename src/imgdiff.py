#!/usr/bin/env python

import sys
from PIL import Image, ImageDraw


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: {} <image 1> <image 2>'.format(sys.argv[0]))
        sys.exit(-1)

    image1 = Image.open(sys.argv[1])
    image2 = Image.open(sys.argv[2])

    mat1 = image1.load()
    mat2 = image2.load()

    if image1.size != image2.size:
        print('Sizes differ')
        sys.exit(-1)

    width, height = image1.size

    for y in xrange(height):
        for x in xrange(width):
            pos = (x, y)

            if mat1[pos] != mat2[pos]:
                print('Pixels differ at {}'.format(pos))

    print('Images are identical.')
    sys.exit(0)
