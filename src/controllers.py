class ControllerBase(object):

    # Control Commands
    def startCommand(self, fileName):
        raise NotImplementedError

    def stopCommand(self):
        raise NotImplementedError

    def pauseCommand(self):
        raise NotImplementedError

    def resumeCommand(self):
        raise NotImplementedError

    # Positional Commands
    def homeCommand(self):
        raise NotImplementedError

    def absoluteMovementCommand(self, x, y):
        raise NotImplementedError

    def incrementalMovementCommand(self, axis, steps):
        raise NotImplementedError

    # Printing Commands
    def firingCommand(self, primitives1, address1, primitives2, address2):
        raise NotImplementedError

class ParsingControllerBase(ControllerBase):
    OP_FIRING = 1
    OP_MOVE = ord('M')

    def supportedCommands(self):
        commands = [
            {
                'name': 'OP_FIRING',
                'opcode': 1,
                'handler': self.__firingCommand__
            },
            {
                'name': 'OP_INCREMENTAL_MOVE',
                'opcode': ord('M'),
                'handler': self.__incrementalMovementCommand__
            }
        ]

        return commands

    def __incrementalMovementCommand__(self, source):
        # Read until the next newline (\n).
        packet = source.readline()
        packet = packet.split()

        axis = str(packet[1])
        steps = int(packet[2])

        self.incrementalMovementCommand(axis, steps)

    def decodePrimitiveBitmask(self, bitmask):
        firings = []

        for i in xrange(8):
            if bitmask & (1 << i):
                firings.append(i)

        return firings

    def __firingCommand__(self, source):
        packet = source.read(8)

        primitive1 = ord(packet[1])
        address1 = ord(packet[2])

        primitive2 = ord(packet[5])
        address2 = ord(packet[6])

        primitive1 = self.decodePrimitiveBitmask(primitive1)
        primitive2 = self.decodePrimitiveBitmask(primitive2)

        self.firingCommand(primitive1, address1, primitive2, address2)


class TestParsingController(ParsingControllerBase):
    positions = {'X': 0, 'Y': 0}
    maximums  = {'X': 0, 'Y': 0}

    def incrementalMovementCommand(self, axis, steps):
        #print('incrementalMovementCommand on {} axis for {} steps.'.format(axis, steps))
        increment = abs(steps)

        if increment > 0:
            self.positions[axis] += increment
        elif increment == 0:
            #print('Homing {} axis.'.format(axis))
            self.positions[axis] = 0
        #else:
        #    print('Negative movement: {} on {} [{}].'.format(increment, axis, positions[axis]))

        for axis in self.positions:
            if self.positions[axis] > self.maximums[axis]:
                self.maximums[axis] = self.positions[axis]

    def firingCommand(self, primitives1, address1, primitives2, address2):
        #print('firingCommand1 on primitives {} (bitmask) and address {}.'.format(primitives1, address1))
        #print('firingCommand2 on primitives {} (bitmask) and address {}.'.format(primitives2, address2))
        pass
