
import sys
import io

class PrintFile:
    file = None
    fileName = None
    fileSize = 0

    def __init__(self, fileName, commandHandler=None):
        self.fileName = fileName

        self.file = io.open(self.fileName, mode='rb')

        self.fileSize = self.file.seek(0, io.SEEK_END)
        self.rewind()

    def rewind(self):
        self.file.seek(0, io.SEEK_SET)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        packet = self.nextCommand()

        if packet:
            return packet
        else:
            raise StopIteration

    def nextCommand(self):
        byte = self.file.read(1)

        if not byte:
            return None

        opcode = ord(byte[0])

        if opcode == 1:
            firing_data = self.file.read(7)

            primitive1 = ord(firing_data[0])
            address1 = ord(firing_data[1])
            primitive2 = ord(firing_data[4])
            address2 = ord(firing_data[5])

            ret = (
                'firing',
                [[primitive1, address1], [primitive2, address2]]
            )

            return ret

        if opcode == ord('M'):
            movement_data = self.file.readline()

            movement_data = movement_data.split()

            axis = movement_data[0]
            steps = movement_data[1]

            ret = (
                'move',
                [{axis: steps}]
            )

            return ret

        print('Unknown Code: {}'.format(opcode))
        return None
