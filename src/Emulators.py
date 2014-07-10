from PIL import Image, ImageDraw

class Printer(object):
    '''
    Printer class.
    '''

    __type__ = 'Printer Base'

    currentPosition = (0, 0)
    printAreaBounds = (0, 0)

    cartridge = None

    cartridgeSlots = [(0, 0)]

    debug = False

    def __init__(self, cartridge, printAreaBounds):
        self.printAreaBounds = printAreaBounds

        self.cartridge = cartridge

    def debug(self, string):
        if self.debug == True:
            print string

    def fire(self, cartridge, primitive, column):
        self.debug('Firing command issued for primitive {} -> {}'.format(primitive, column))

        if len(column) != self.cartridge.addresses:
            print 'Column size mis-match, aborting firing command.'
            return False

        if primitive >= self.cartridge.primitives:
            print 'Primitive out of range.', primitive, self.cartridge.primitives
            return False

        if cartridge > len(self.cartridgeSlots):
            print 'Cartridge out of range.', cartridge, self.cartridgeSlots
            return False

        return True

    # Helper Functions
    def getX(self):
        return self.currentPosition[0]

    def getY(self):
        return self.currentPosition[1]

    def getBoundsX(self):
        return self.printAreaBounds[0]

    def getBoundsY(self):
        return self.printAreaBounds[1]

    def moveTo(self, x, y):
        if self.checkBounds(x, y):
            self.currentPosition = (x, y)
        else:
            print 'Attempted to move beyond bed boundary.', self.printAreaBounds

    def moveToX(self, x):
        if self.checkBounds(x, None):
            self.currentPosition = (x, self.getY())
        else:
            print 'Attempted to move beyond bed boundary.', self.printAreaBounds

    def moveToY(self, y):
        if self.checkBounds(None, y):
            self.currentPosition = (self.getX(), y)
        else:
            print 'Attempted to move beyond bed boundary.', self.printAreaBounds

    def checkBounds(self, x, y):
        if x:
            if x < 0 or x >= self.getBoundsX():
                return False
        if y:
            if y < 0 or y >= self.getBoundsY():
                return False

        return True

    def incrementX(self, xIncrement=1, wrap=False):
        newX = self.getX() + xIncrement

        if not self.checkBounds(newX, None):
            newX = newX - self.getBoundsX()

            if wrap == True:
                self.advanceY()

        self.moveToX(newX)

    def advanceX(self):
        self.incrementX()

    def incrementY(self, yIncrement=1):
        newY = self.getY() + yIncrement

        if not self.checkBounds(None, newY):
            print 'Hit bottom of printable bounds, advancing as far as possible.'
            newY = self.getBoundsY()

        self.moveToY(newY)

    def advanceY(self):
        # This is multiplied by 2, since we're taking advantage of the column offsets
        # to produce 600 dpi, so primitive is effectively double spaced.
        self.incrementY(self.cartridge.addresses * 2)

    def __str__(self):
        return '{}, equipped with a {}'.format(self.__type__, self.cartridge)
        #return 'Head currently at {}'.format(self.currentPosition)


class Cartridge(object):
    nozzles = None
    primitives = None
    addresses = None
    columns = None
    horizontalSpacing = None
    verticalSpacing = None

    __type__ = 'Abstract HP InkJet Cartridge'

    inkColour = None

    # 104 Nozzles
    # 8 Primitives
    # 13 Addresses
    # 2 Columns
    
    # 12 Horizontal Spacing
    # 0 Vertical Spacing
    def __init__(self, nozzles, primitives, addresses, columns, horizontalSpacing, verticalSpacing):
        self.nozzles = nozzles
        self.primitives = primitives
        self.addresses = addresses
        self.columns = columns
        self.horizontalSpacing = horizontalSpacing
        self.verticalSpacing = verticalSpacing

    def offsetForPrimitive(self, primitive):
        return (0, 0)

    def indexForNozzle(self, nozzle):
        return (nozzle / self.columns) % self.addresses

    def columnForNozzle(self, nozzle):
        return nozzle % self.columns

    def primitiveForNozzle(self, nozzle):
        column = self.columnForNozzle(nozzle)

        # This is really (nozzle / ( columns * primitive_size) * columns + my_column)
        # NOTE: The columns CANNOT cancel out, since we're relying on integer rounding
        # ocurring before the second multiplication
        return (nozzle / (self.columns * self.addresses)) * self.columns + column

    def addressForPrimitiveIndex(self, primitive, index):
        # This needs to be implemented in the subclass
        raise NotImplementedError

    def __str__(self):
        return '{}. {} total nozzles ({} columns), arranged in {} primitives of {} nozzles each.'.format(self.__type__,
                self.nozzles, self.columns, self.primitives, self.addresses)
