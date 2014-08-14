from Emulators import Printer, Cartridge

from PIL import Image, ImageDraw
from datetime import datetime

class Argentum(Printer):
    '''
    Argentum Simulatron
    '''
    HEADOFFSET = 1365

    cartridgeSlots = ((0, 0), (0, HEADOFFSET))
    __type__ = 'Argentum'

    def __init__(self):
        super(Argentum, self).__init__(HP_CC(), (1907, 1907))

class ArgentumEmulator(Printer):
    printImage = None
    printMatrix = None

    __type__ = 'Argentum Simulator'

    def __init__(self, cartridge, printAreaBounds):
        super(ArgentumEmulator, self).__init__(HP_CC(), (1907, 1907))

        self.printImage = Image.new('RGBA', self.printAreaBounds, (0, 0, 0, 0))

        self.printMatrix = self.printImage.load()

    def stampImage(self):
        self.placeTextOnPrintImage('Printed on a [{}] at {}'.format(self.__type__, datetime.now()), (0, 0))
        self.placeTextOnPrintImage(self.cartridge.__str__(), (0, 10))

        #printScale = PrintScale()
        #printScale.drawAtLocation(self.printImage, (0, self.printImage.size[1] - 48))

    def placeTextOnPrintImage(self, text, origin):
        imageContext = ImageDraw.Draw(self.printImage)
        imageContext = imageContext.text(origin, text, (0, 0, 0))

    def savePrintToFile(self, filename=None):
        if self.printImage:
            if(filename == None):
                filename = '{} - {}.png'.format(self.__type__, datetime.now().strftime("%y%m%d-%H%M%S"))

            self.stampImage()
            self.printImage.save(filename)

    def fire(self, cartridge, primitive, column):
        validation = super(ArgentumEmulator, self).fire(cartridge, primitive, column)

        #if not validation:
        #    return validation

        y = 0;

        cartridgeXOffset, cartridgeYOffset = self.cartridgeSlots[cartridge]

        for pixel in column:
            if pixel:
                # if(self.getY() + y < self.getBoundsY):
                pixelOffset = (y * self.cartridge.columns)

                primitiveXOffset, primitiveYOffset = self.cartridge.offsetForPrimitive(primitive)

                xPosition = self.getX() + primitiveXOffset + cartridgeXOffset
                yPosition = self.getY() + pixelOffset + primitiveYOffset + cartridgeYOffset

                if self.checkBounds(xPosition, yPosition):
                    self.printMatrix[xPosition, yPosition] = self.cartridge.inkColour

            y = y + 1


class HP_CC(Cartridge):
    __type__ = 'HP Something'
    inkColour = (255, 0, 0)

    def __init__(self):
        super(HP_CC, self).__init__(104, 8, 13, 2, 12, 0)

    def offsetForPrimitive(self, primitive):
        xOffset = 0
        yOffset = 0

        if(primitive % 2 == 0):
            # If the primitive is even, we move BACKWARD
            xOffset = -self.horizontalSpacing

            # The real equation
            # yOffset = ((primitive / 2) * self.addresses * 2) + 1
            # We divide the primitive by 2, since they're split evenly between the columns
            # and multiply addresses by 2 since they're double spaced for the DPI increase
            # The + 1 is because it's the even side that is offset for 600 DPI
            yOffset = primitive * self.addresses + 1
        else:
            xOffset = 0

            # We can subtract 1 here without concern for it going negative, since we know
            # the number must be odd (and > 0)
            yOffset = (primitive - 1) * self.addresses

        return (xOffset, yOffset)

    def addressForPrimitiveIndex(self, primitive, index):
        if(primitive % 2) == 0:
            index = index + 4
        else:
            index = index + 7

        address = (1 + (index * 4)) % self.addresses

        # This is because of the modulus, we can never have an actual
        # value of zero here (because our address lines are offset)
        # in the multiplexer hardware, so this should be fine
        if address == 0:
            address = 13

        return address
