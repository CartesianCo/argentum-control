#!/usr/bin/env python

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
