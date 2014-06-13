from PIL import Image
### Image Processing Functions

class ImageProcessor:
    # Define Constants
    HEADOFFSET = 1365        # Distance between the same line of primitives on two different heads (in pixels)
    PRIMITIVEOFFSET = 12     # Distance between two different primitives on the same head (in pixels)
    VOFFSET = 0              # Vertical distance between the two printheads
    SPN = 3.386666           # Steps per nozzle (actually per half nozzle as we are doing 600 dpi)

    # Movement offset in pixels. This is how far down we move between lines.
    # Can be changed to any odd number less than 103. A larger number means the
    # print will be faster but put down less ink and have less overlap
    mOffset = 41

    # Firings per step variable. Currently cannot set different firings per step for
    # different print heads but this will be implemented very soon - won't take me
    # long to implement.
    fps = 1

    def sliceImage(self, outputFileName, inputFileName):
        #directory = direct
        # Global variables to hold the images we are working with
        global outputImages
        global pixelMatrices

        outputImages = []
        pixelMatrices = []

        outputFile = open(outputFileName, 'wb')

        # Go to our working directory and open/create the output file
        #os.chdir(directory)
        hexOutput = outputFile

        # Open our image and split it into its odd rows and even rows
        inputImage = Image.open(inputFileName)

        inputs = self.splitImageTwos(inputImage)

        # Get the size of the input images and adjust width to be that of the output
        width, height = inputs[0].size
        width += self.HEADOFFSET + self.PRIMITIVEOFFSET

        # Adjust the height. First make sure it is divisible by 25. Then add an
        # extra 2 rows of blank lines.
        height += (self.mOffset - height % self.mOffset)
        height += (int(208/self.mOffset) * self.mOffset)
        #height += (104*2)

        # Create the output images and put them into a tuple for easy referencing
        outputImages = [Image.new('RGBA', (width,height), (255,255,255,255)) for i in range(4)]

        # Paste the split input image into correct locations on output images
        pasteLocations = (
            (self.HEADOFFSET, (int(208/self.mOffset) * self.mOffset)/2),
            (self.HEADOFFSET+self.PRIMITIVEOFFSET, (int(208/self.mOffset) * self.mOffset)/2),
            (0, (int(208/self.mOffset) * self.mOffset)/2 + self.VOFFSET),
            (self.PRIMITIVEOFFSET, (int(208/self.mOffset) * self.mOffset)/2 + self.VOFFSET)
        )

        for i in range(4):
            outputImages[i].paste(inputs[i%2], pasteLocations[i])
            #outputImages[i].show()

        #pixelMatrices = (outputImages[0][0].load(), outputImages[0][1].load(),
        #outputImages[0][2].load(), outputImages[0][3].load())
        pixelMatrices = [outputImages[i].load() for i in range(4)]

        # We have our input images and their matrices. Now we need to generate the
        # correct output data.
        self.writeCommands(hexOutput)

        # Construct image from Output.hex
        #simulateImage()



    def writeCommands(self, outputStream):

        width, height = outputImages[0].size
        height -= (int(208/self.mOffset) * self.mOffset) # Ignore empty pixels added to the bottom of the file.
        print height
        # Move right 400 steps
        #outputStream.write('M X 3000\n')

        yposition = 0

        for y in range(height/self.mOffset*2 + 1):

            # Print out progress
            print '{} out of {}.'.format(y + 1, height/self.mOffset*2 + 1)

            move = 0
            xposition = 0

            # Iterate through the width of the image(s)
            for x in range(width):

                firings = [[self.calculateFiring(x, y, a, 0), self.calculateFiring(x, y, a, 1)] for a in range(13)]

                if not any([any(firings[i]) for i in range(len(firings))]):
                    #move += (int((x + 1) * SPN) - xposition - move)
                    move = (int((x + 1) * self.SPN) - xposition)
                    continue
                elif move != 0 :
                    xposition += move
                    outputStream.write('M X %d\n' % move)
                    move = (int((x + 1) * self.SPN) - xposition)

                for f in range(self.fps):
                    # Iterate through addresses
                    for a in range(13):
                        if firings[a] == [0, 0]:
                            continue

                        for i in range(2):
                            #outputStream.write(chr(1))
                            #outputStream.write(chr(firings[a][i]))
                            #outputStream.write(chr(a + 1))
                            #outputStream.write(chr(0))

                            address = ((a + 1) & 0b00000001) << 3
                            address += ((a + 1) & 0b00000010) << 1
                            address += ((a + 1) & 0b00000100) >> 1
                            address += ((a + 1) & 0b00001000) >> 3

                            if 1 == 1:
                                outputStream.write(chr(1)) # Fire command
                                outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                                outputStream.write(chr(address)) # The address we are firing on
                                outputStream.write(chr(0))

                            if 1 == 0:

                                if y % 4 == 0:
                                    outputStream.write(chr(1)) # Fire command
                                    outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                                    outputStream.write(chr(address)) # The address we are firing on
                                    outputStream.write(chr(0))


            # Move back
            #print xposition
            #if xposition != 0:
                #outputStream.write('M X %d\n' % -xposition)
                #print xposition
                #xposition = 0
            if xposition != 0:
                outputStream.write('M X 0\n')
                xposition = 0

            # Move down

            movey = int(self.mOffset * (y + 1) * self.SPN) - yposition
            outputStream.write('M Y %d\n' % -movey)
            yposition += movey


        # Reset X and Y positions

        outputStream.write('M Y 0\n')
        outputStream.write('M X 0\n')




        outputStream.close()



    def calculateFiring(self, xPos, yPos, addr, side):

        # Lookup tables to convert address to position
        positions = ((0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3), (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12))

        firing = 0

        x = xPos
        y = (yPos * self.mOffset)/2 + (positions[0][addr] * 2)
        if yPos % 2: y += 1
        for i in range(4):
            if pixelMatrices[side*2][x, y][2] <= 200:
                firing += 1 << (i*2)
            y += 26

        y = (yPos * self.mOffset)/2 + (positions[1][addr] * 2)
        if yPos % 2: y += 1
        for i in range(4):
            if pixelMatrices[side*2 + 1][x, y][2] <= 200:
                firing += 1 << (i*2 + 1)
            y += 26

        return firing

    '''
    Splits an input image into two images.
    '''
    def splitImageTwos(self, image):
        width, height = image.size

        if height % 4 != 0:
            height += (4 - (height % 4))

        odd = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))
        even = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))

        evenMatrix = even.load()
        oddMatrix = odd.load()
        inputMatrix = image.load()

        for y in range((height / 4) - 1):
            for x in range(width):
                oddMatrix[x, y*2] = inputMatrix[x, y*4]
                oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]
                evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
                evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

        y = (height / 4) - 1
        for x in range(width):
            if y*4 < image.size[1]: oddMatrix[x, y*2] = inputMatrix[x, y*4]
            if y*4 + 1 < image.size[1]: oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]
            if y*4 + 2 < image.size[1]: evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
            if y*4 + 3 < image.size[1]: evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

        return (odd, even)
