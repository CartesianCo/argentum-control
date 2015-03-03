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

class HP40Cartridge():
    ##################################################
    #################### CONSTANTS ###################
    ##################################################

    # Native resolution of the spacing between nozzles of the cartridge in DPI.
    nativeRes = 300

    # Number of nozzle columns on the cartridge printhead.
    numColumns = 2

    # This is the horizontal offset of one column relative to another in native pixels.
    columnOffsetNativePx = 6

    # Number of primitives in the cartridge driving architecture.
    numPrimitives = 8

    # Number of addresses in the cartridge driving architecture.
    numAddresses = 13

    # Ratio of image pixels to native pixels.  The default is 2 which implies a 600DPI
    # image relative to the 300DPI native resolution.
    imagePxPerNativePx = 2

    # The average drop volume ejected from a single firing in the cartridge.
    avgDropVolume = 130

    # The volume of the ink reservoir that the cartridge holds.
    reservoirVolume = 42

    # This is a mapping of an address index to the corresponding nozzle number, first for an
    # odd primitive and then an even.  Please see geometry below for more details.
    oddMap = (1,21,15,9,3,23,17,11,5,25,19,13,7)
    evenMap = (20,14,8,2,22,16,10,4,24,18,12,6,26)

    '''    
    ##################################################
    #################### GEOMETRY ####################
    ##################################################
    
    The following commented section outlines the geometry of primitives on the nozzle plate
    & nozzles within the primitive.  This information is then used to synthesize functions
    that can provide displacement of any nozzle (given by its address and primitive) from
    the top-most nozzle of the cartridge (which is used as an origin for all displacements).
    
    ##################################################
    ##### ARRANGEMENT OF PRIMITIVES IN CARTRIDGE #####
    ##################################################

    # This is the bottom view of the nozzle (ie. as if you picked up a cartridge
    # and looked at the nozzle plate while holding the cartridge upside down).
    # This representation is shown as it is how the information is presented in the patent.
 
        EVEN     ODD
                   |
           |    P1 |
        P2 |       |
           |
                   |
           |    P3 |
        P4 |       |
           |
                   |
           |    P5 |
        P6 |       |
           |
                   |
           |    P7 |
        P8 |       |
           |
           
    # This is the top view of the nozzle (ie. as if you were looking down on the nozzle
    # plate through the cartridge body as it's installed in a printer).  This is the way
    # that the primitives are referenced for generating data because a top down view will
    # prevent requiring a flipping of the input image.
    
        ODD     EVEN
           |
        P1 |       |
           |    P2 |
                   |
           |
        P3 |       |
           |    P4 |
                   |
           |
        P5 |       |
           |    P6 |
                   |
           |
        P7 |       |
           |    P8 |
                   |

    NOTE: P1/P2 are referred to as a primitive pair
    as are P4/P3, P5/P6 & P7/P8.
    NOTE: that primitives are 0 indexed in code, therefore
    P1 is equivalent to index 0 & P8 is equivalent to index 7

    ##################################################
    #### ARRANGEMENT OF NOZZLES IN ODD PRIMITIVES ####
    ##################################################

    # NOTE: This is a bottom view of the nozzles in a primitive (ie. as if you picked up a
    # cartridge and looked at the nozzle plate while holding the cartridge upside down).
    # This representation is shown as it is how the information is presented in the patent.

    (A01)        1 ●
    (A05)            3 ●
    (A09)                5 ●
    (A13)                    7 ●
    (A04)          9 ●
    (A08)             11 ●
    (A12)                 13 ●
    (A03)         15 ●
    (A07)             17 ●
    (A11)                 19 ●
    (A02)         21 ●
    (A06)             23 ●
    (A10)                 25 ●

    # NOTE: This is a top view of the nozzles in a primitive(ie. as if you were looking down
    # on the nozzle plate through the cartridge body as it's installed in a printer).  This
    # is the way that the primitives are referenced for generating data because a top down
    # view will prevent requiring a flipping of the input image.

    (A01)                    1 ●
    (A05)                3 ●
    (A09)            5 ●
    (A13)       7 ●
    (A04)                  9 ●
    (A08)             11 ●
    (A12)         13 ●
    (A03)                 15 ●
    (A07)             17 ●
    (A11)         19 ●
    (A02)                 21 ●
    (A06)             23 ●
    (A10)         25 ●
    
    ##################################################
    ### ARRANGEMENT OF NOZZLES IN EVEN PRIMITIVES ####
    ##################################################

    # NOTE: This is a bottom view of the nozzles in a primitive (ie. as if you picked up a
    # cartridge and looked at the nozzle plate while holding the cartridge upside down).
    # This representation is shown as it is how the information is presented in the patent.

    (A04)          2 ●
    (A08)              4 ●
    (A12)                  6 ●
    (A03)          8 ●
    (A07)             10 ●
    (A11)                 12 ●
    (A02)         14 ●
    (A06)             16 ●
    (A10)                 18 ●
    (A01)       20 ●
    (A05)           22 ●
    (A09)               24 ●
    (A13)                   26 ●

    # NOTE: This is a top view of the nozzles in a primitive(ie. as if you were looking down
    # on the nozzle plate through the cartridge body as it's installed in a printer).  This
    # is the way that the primitives are referenced for generating data because a top down
    # view will prevent requiring a flipping of the input image.


    (A04)                  2 ●
    (A08)              4 ●
    (A12)          6 ●
    (A03)                  8 ●
    (A07)             10 ●
    (A11)         12 ●
    (A02)                 14 ●
    (A06)             16 ●
    (A10)         18 ●
    (A01)                   20 ●
    (A05)               22 ●
    (A09)           24 ●
    (A13)      26 ●
    
    NOTE:
    Vertical displacement between nozzles 1 & 3 =  & 9 = 2 & 4 etc...
    Vertical displacement between nozzles in one column = nativePixelWidth * 2
    In the case of the HP 40, nativePixelWidth = 25.4/300 (300DPI)
    In the case of the HP 45, nativePixelWidth = 25.4/600 (600DPI)

    ##################################################
    ##### MAPPING AN ADDRESS TO A NOZZLE NUMBER ######
    ##################################################

    The information on Arrangement of Nozzles in Primitives (found above) is re-arranged
    here to be in order of ascending address index.  This allows for a simple mapping from
    address index to nozzle number (within the primitive pair).

        ODD PRIMITIVE       EVEN PRIMITIVE
        A01 -> 1            A01 -> 20
        A02 -> 21           A02 -> 14
        A03 -> 15           A03 -> 8
        A04 -> 9            A04 -> 2
        A05 -> 3            A05 -> 22
        A06 -> 23           A06 -> 16
        A07 -> 17           A07 -> 10
        A08 -> 11           A08 -> 4
        A09 -> 5            A09 -> 24
        A10 -> 25           A10 -> 18
        A11 -> 19           A11 -> 12
        A12 -> 13           A12 -> 6
        A13 -> 7            A13 -> 26

    NOTE: that addresses are 0 indexed in code, therefore
    A01 is equivalent to index 0 & A13 is equivalent to index 12
    NOTE: the isEvenPrimitive value is slightly misleading because values
    are 0 indexed.  If the primitive index is odd, then PX%2 = 1 and isEvenPrimitive
    is true.
    '''

    def __init__(self, imageRes=None):

        if (imageRes):
            # The default imageRes is 600DPI.  If you would like to print in 300DPI,
            # set imageRes to 300 and self.imagePxPerNativePx will = 1.
            self.imagePxPerNativePx = imageRes/self.nativeRes

        # This is the height of a single primitive in image pixels.
        self.primitiveHeight = ((self.imagePxPerNativePx * 2) * self.numAddresses)

        # This is the height of the full swath of the nozzle plate in image pixels.
        # NOTE: that the cartridge may not be able to print all rows in a given swath height,
        # this is simply the height of image it traverses.
        self.swathHeight = (self.numPrimitives * self.numAddresses) * self.imagePxPerNativePx

        # This is the horizontal offset of one column relative to another in image pixels.
        self.columnOffset = self.columnOffsetNativePx * self.imagePxPerNativePx

    def findNozzleInPrimitive(self, address, isEvenPrimitive):
        '''
        This uses the mapping defined in the class def comments to return the nozzle 'number'
        from a given address and whether the primitive is even or odd.  This can in turn
        be used to determine its displacement.
        '''
        if (isEvenPrimitive):
            return self.evenMap[address]
        else :
            return self.oddMap[address]

    def addressDisplacement(self, address, primitive):
        '''
        Used to get the vertical displacement from the first nozzle (in image px)of a given
        primitive pair of a given primitive and for a given address.
        NOTE: before multiplying by self.imagePxPerNativePx, if the primitive is an even
        primitive, the displacement will be even and vice versa.  This is important as it
        delegates different information to each column.
        '''
        return (self.findNozzleInPrimitive(address, primitive%2) - 1) \
               * self.imagePxPerNativePx

    def primitiveDisplacement(self, primitive):
        '''
        Used to get the vertical displacement (in image px) of the first nozzle in a given
        primitive from the first nozzle in P1.
        '''
        return primitive/2 * self.primitiveHeight

    def verticalNozzleDisplacement(self, address, primitive):
        '''
        Used to get the vertical displacement (in image px) from the top nozzle of the
        cartridge for any nozzle with a given primitive and given address.
        '''
        return self.primitiveDisplacement(primitive) \
               + self.addressDisplacement(address, primitive)

    def horizontalNozzleDisplacement(self, primitive):
        '''
        Used to get the horizontal displacement (in image px) from the top nozzle of the
        cartridge for any primitive.  Note that this function *DOES NOT* account for the
        variation in horizontal position within a column.
        '''
        if (primitive % 2 == 1):
            # The primitive is an even primitive.
            # Therefore the horizontal offset is equal to the columnOffset left.
            return (-self.columnOffset)
        else:
            # The primitive is an even primitive.
            # Therefore the horizontal offset is 0.
            return 0

    def nozzleDisplacement(self, address, primitive):
        '''
        Used to get the horizontal and vertical displacement (in image px) from the top
        nozzle of the cartridge for any primitive.  Note that this function *DOES NOT*
        account for the variation in horizontal position within a column.
        Return format is tuple as (horizontal displacement, vertical displacement).
        '''
        return (self.horizontalNozzleDisplacement(primitive), \
                self.verticalNozzleDisplacement(address, primitive))


'''
For example:

We are printing a 600DPI image with a HP 40 cartridge (native resolution 300DPI).

We need to find the vertical displacement from the top of a swath of a given nozzle,
given by its primitive (P3, note index 2) and its address (A05, note index 4).

imagePxPerNativePx = imageRes/nativeRes
                   = 600 / 300
                   = 2
This means that the width of the image pixels are 1/2 the width of the native resolution
ofthe cartridge.  We use this number to scale our displacements into image pixels.

findNozzleInPrimitive(4, 2%2) = 3
If we check this with the the diagram above for an odd primitive, we see that it is correct.

addressDisplacement(4,2) = (findNozzleInPrimitive(4, 2%2) - 1) * imagePxPerNativePx
                       = (3 - 1) * imagePxPerNativePx
                       = 4
This means that the nozzle is offset 4 pixels vertically from the top nozzle of its
primitive pair.

heightOfPrimitive = (13 * (imagePxPerNativePx * 2))
                  = 13 * (2 * 2)
                  = 13 * (4)
                  = 52
This means that a whole primitive is 52 pixels high.

The primitiveDisplacement(2) = 2/2 * heightOfPrimitive
                             = 1 * 52
                             = 52
This means that the first nozzle in the second primitive pair is 52 pixels down from the
top nozzle in the cartridge.

displacement = primitiveDisplacement(2) + addressDisplacement(4,2)
             = 52 + 4
             = 56
Therefore the total displacement from the top nozzle of the cartridge is 56 image pixels.

It is interesting to note that if imagePxPerNativePx is an even number (such as 2 in this
case) the displacement will always be even.  This is because the cartridge can only reach
the 0th, 2nd, 4th, 6th, ... pixel rows relative to the top nozzle in the cartridge.  This
is why it is important to make the feed advance an odd number of pixels.
'''
