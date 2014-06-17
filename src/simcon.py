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
        #print('firingCommand1 on primitives {} (bitmask) and address {}.'.format(primitives1, address1))
        #print('firingCommand2 on primitives {} (bitmask) and address {}.'.format(primitives2, address2))
        pass
