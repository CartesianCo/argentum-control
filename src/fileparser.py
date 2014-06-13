#!/usr/bin/python

import sys
import io

OP_FIRING = 1
OP_MOVE = ord('M')
CMD_TERMINATOR = '\n'

def peekByte(fileStream):
    byte = fileStream.peek(1)

    if byte:
        return byte[0]
    else:
        return None

def nextByte(fileStream):
    return fileStream.read(1)

print('Argentum File Parser')

if len(sys.argv) < 2:
    print('usage: {} <filename>'.format(sys.argv[0]))
    sys.exit(-1)

inputFileName = sys.argv[1]
inputFile = io.open(inputFileName, mode='rb')

byte = peekByte(inputFile)

while byte:
    #print byte
    byte = ord(byte)

    if byte == OP_FIRING:
        #print('Got firing command.')

        packet = inputFile.read(8) # Burn 7 bytes for now

        print('{},{} - {},{}'.format(ord(packet[1]), ord(packet[2]), ord(packet[5]), ord(packet[6])))

    if byte == OP_MOVE:
        #print('Got movement command.')

        packet = inputFile.readline()

        #print(packet[:-1])

    byte = peekByte(inputFile)
    #a = input('')
