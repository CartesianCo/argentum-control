
# Import Libraries
from PIL import Image          # image processing library
import os             # library for handling actions like changing directory
import tkMessageBox, tkFileDialog
from Tkinter import Tk

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

#directory = "C:\Users\Mike\Dropbox\Cartesian Co\Software\John\Computer Side" # Location of files, change to your dropbox
outputFile = "Output.hex"
#imageFile = "matrixModuleSilver.png"                # The image we are working with



def tempInitiate():
    #temp = Tk()
    #printFilePath = tkFileDialog.askopenfilename(filetypes = [
    #        ("GIF Images", "*.GIF"),
    #        ("BMP Images", "*.BMP"), ("PNG Images", "*.PNG"),
    #        ("Jpeg Images", "*.JPG"), ("All Files", "*")])
    #temp.destroy()
    printFilePath = "input.jpg"
    if printFilePath:
        image = Image.open(printFilePath)
        sliceImage("./", image)


def sliceImage(direct, inputImage):
    directory = direct
    # Global variables to hold the images we are working with
    global outputImages
    global pixelMatrices

    outputImages = []
    pixelMatrices = []

    # Go to our working directory and open/create the output file
    os.chdir(directory)
    hexOutput = open(outputFile, "wb")

    # Open our image and split it into its odd rows and even rows
    #inputImage = Image.open(imageFile)
    inputs = splitImageTwos(inputImage)

    # Get the size of the input images and adjust width to be that of the output
    width, height = inputs[0].size
    width += HEADOFFSET + PRIMITIVEOFFSET

    # Adjust the height. First make sure it is divisible by mOffset. Then add an
    # extra 2 rows of blank lines.
    height += (mOffset - height%mOffset)
    height += (int(208/mOffset) * mOffset) # mOffset cancels out here, could just += 208 (2 * nozzle rows)
    #height += (104*2)

    # Create the output images and put them into a tuple for easy referencing
    outputImages = [Image.new('RGBA', (width,height), (255,255,255,255)) for i in range(4)]

    """
    HEADOFFSET = 1365        # Distance between the same line of primitives on two different heads (in pixels)
    PRIMITIVEOFFSET = 12     # Distance between two different primitives on the same head (in pixels)
    VOFFSET = 0              # Vertical distance between the two printheads
    SPN = 3.386666
    """

    # Paste the split input image into correct locations on output images
    pasteLocations = ((HEADOFFSET, (int(208/mOffset) * mOffset)/2),                     # (HEADOFFSET, 104)
                      (HEADOFFSET+PRIMITIVEOFFSET, (int(208/mOffset) * mOffset)/2),     # (HEADOFFSET + PRIMITIVEOFFSET, 104)
                      (0, (int(208/mOffset) * mOffset)/2 + VOFFSET),                    # (0, VOFFSET + 104)
                      (PRIMITIVEOFFSET, (int(208/mOffset) * mOffset)/2 + VOFFSET))      # (PRIMITIVEOFFSET, VOFFSET + 104)

    # (HEADOFFSET, 104) = (1365, 104)
    # (HEADOFFSET + PRIMITIVEOFFSET, 104) = (1377, 104)
    # (0, VOFFSET + 104) = (0, 104)
    # (PRIMITIVEOFFSET, VOFFSET + 104) = (12, 104)

    for i in range(4):
        outputImages[i].paste(inputs[i%2], pasteLocations[i])
        #outputImages[i].show()

    #pixelMatrices = (outputImages[0][0].load(), outputImages[0][1].load(),
    #outputImages[0][2].load(), outputImages[0][3].load())
    pixelMatrices = [outputImages[i].load() for i in range(4)]

    outputImages[0].save("0.png");
    outputImages[1].save("1.png");
    outputImages[2].save("2.png");
    outputImages[3].save("3.png");

    # We have our input images and their matrices. Now we need to generate the
    # correct output data.
    writeCommands(hexOutput)

    # Construct image from Output.hex
    #simulateImage()



def writeCommands(outputStream):

    width, height = outputImages[0].size
    height -= (int(208/mOffset) * mOffset) # Ignore empty pixels added to the bottom of the file.
    print height
    # Move right 400 steps
    #outputStream.write('M X 3000\n')

    yposition = 0

    for y in range(height/mOffset*2 + 1):

        # Print out progress
        print '{} out of {}.'.format(y + 1, height/mOffset*2 + 1)

        move = 0
        xposition = 0

        # Iterate through the width of the image(s)
        for x in range(width):

            firings = [[calculateFiring(x, y, a, 0), calculateFiring(x, y, a, 1)] for a in range(13)]

            # if not any([any(firings[i]) for i in range(len(firings))]):
            #     #move += (int((x + 1) * SPN) - xposition - move)
            #     move = (int((x + 1) * SPN) - xposition)
            #     continue
            # elif move != 0 :
            #     xposition += move
            #     outputStream.write('M X %d\n' % move)
            #     move = (int((x + 1) * SPN) - xposition)

            if any([any(firings[i]) for i in range(len(firings))]):
                if move != 0 :
                    xposition += move
                    outputStream.write('M X %d\n' % move)

            move = (int((x + 1) * SPN) - xposition)

            for f in range(fps):
                # Iterate through addresses
                for a in range(13):
                    if firings[a] == [0, 0]:
                        continue

                    for i in range(2):
                        #outputStream.write(chr(1))
                        #outputStream.write(chr(firings[a][i]))
                        #outputStream.write(chr(a + 1))
                        #outputStream.write(chr(0))


                        # NOTE: I don't think this will work correctly, pretty sure it should be OR instead of ADDITION
                        # NOTE: turns out that addition will give the same result as or, as long as the bits you're adding don't cause an overflow
                        # i.e. none of them are already set.
                        address = ((a + 1) & 0b00000001) << 3
                        address += ((a + 1) & 0b00000010) << 1
                        address += ((a + 1) & 0b00000100) >> 1
                        address += ((a + 1) & 0b00001000) >> 3
                        # aa = a + 1
                        # address = 0
                        #
                        # address |= ((aa & 0b0001) << 3)
                        # address |= ((aa & 0b0010) << 1)
                        # address |= ((aa & 0b0100) >> 1)
                        # address |= ((aa & 0b1000) >> 3)

                        if 1 == 1:
                            outputStream.write(chr(1)) # Fire command
                            outputStream.write(chr(firings[a][i])) # Relevant firing data, i.e. which primitive to fire
                            outputStream.write(chr(address)) # The address we are firing on
                            outputStream.write(chr(0))
                            #outputStream.write('Firing for {:n}: {:08b}, address: {:013b}\n'.format(i, firings[a][i], address))

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

        movey = int(mOffset * (y + 1) * SPN) - yposition
        outputStream.write('M Y %d\n' % -movey)
        yposition += movey


    # Reset X and Y positions

    outputStream.write('M Y 0\n')
    outputStream.write('M X 0\n')




    outputStream.close()



def calculateFiring(xPos, yPos, addr, side):

    # Lookup tables to convert address to position
    positions = ((0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3), (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12))

    # 13 nozzles in a primitive, these are the number of the nozzles, in the correct firing order.
    # the second grouping is for the even side? it is simply offset by the first 3 nozzles, which is strange.
    # I would have assumed it to be just the reverse of the first one, to maintain maximum physical distance between firing nozzles.

    # The second one IS for the even side, and by shifting the order 3 settings, you can use the same index to get the
    # correct firing for each primitive.

    firing = 0

    x = xPos
    y = (yPos * mOffset)/2 + (positions[0][addr] * 2)
    if yPos % 2: y += 1

    # 0, 2, 4, 6
    for i in range(4):
        if pixelMatrices[side*2][x, y][2] <= 200:
            firing |= 1 << (i*2)
            #print 'firing A -> x {}, y {}, addr {}, i {}'.format(x, y, addr, i)
        y += 26

    y = (yPos * mOffset)/2 + (positions[1][addr] * 2)
    if yPos % 2: y += 1

    # 1, 3, 5, 7
    for i in range(4):
        if pixelMatrices[side*2 + 1][x, y][2] <= 200:
            firing |= 1 << (i*2 + 1)
            #print 'firing B -> x {}, y {}, addr {}, i {}'.format(x, y, addr, i)
        y += 26

    #if(firing):
    #    print 'Calculating Primitives to fire for ({}, {}), address: {:#013b}, side: {}'.format(xPos, yPos, addr, side)

    return firing


#
# def simulateImage():
#     fileIn = open(outputFile, "r")
#     print os.getcwd()
#     print fileIn.closed
#
#     xPos = 0
#     yPos = 0
#     xMax = 0
#     yMax = 0
#
#     readIn = fileIn.read(1)
#
#     # Calculate what dimensions the output picture is
#     while(readIn != ""):
#
#         # Ignore firing commands
#         if readIn[0] == chr(1):
#             fileIn.read(7)
#
#         if readIn[0] == 'M':
#             readIn = fileIn.read(3)
#             number = fileIn.readline()
#             if readIn[1] == 'X':
#                 if int(number) == 0:
#                     xPos = 0
#                 else:
#                     xPos += int(number)
#                     if xPos > xMax: xMax = xPos
#             elif readIn [1] == 'Y':
#                 if int(number) == 0:
#                     yPos = 0
#                 else:
#                     yPos -= int(number)
#                     if yPos > yMax: yMax = yPos
#
#
#         readIn = fileIn.read(1)
#
#     fileIn.close()
#
#     print xMax, yMax
#
#     outputImage = Image.new('RGBA', (int((xMax)/SPN - HEADOFFSET), int(yMax/SPN) + 208), (255, 255, 255, 255))
#     outputMatrix = outputImage.load()
#
#
#     fileIn = open(outputFile, "r")
#
#     readIn = fileIn.read(1)
#
#     while(readIn != ""):
#
#         if readIn[0] == chr(1):
#             rval = fileIn.read(1)[0]
#             addr = fileIn.read(1)[0]
#             fileIn.read(2)
#             lval = fileIn.read(1)[0]
#             fileIn.read(2)
#             #if ord(addr) == 1:
#                 #print xPos, ord(rval), ord(lval)
#             updateImage(ord(addr), ord(rval), ord(lval), outputMatrix, xPos, yPos)
#
#         if readIn[0] == 'M':
#             readIn = fileIn.read(3)
#             number = fileIn.readline()
#             if readIn[1] == 'X':
#                 if int(number) == 0: xPos = 0
#                 else: xPos += int(number)
#             elif readIn [1] == 'Y':
#                 if int(number) == 0: yPos = 0
#                 else: yPos -= int(number)
#
#         readIn = fileIn.read(1)
#
#
#     outputImage.show()


#
# def updateImage(addr, rval, lval, matrix, xPos, yPos):
#     positions = ((0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3), (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12))
#
#     #imageR1.paste(oddInput, (HEADOFFSET+PRIMITIVEOFFSET, 0))
#     #imageR2.paste(evenInput, (HEADOFFSET, 0))
#     #imageL1.paste(oddInput, (PRIMITIVEOFFSET, 0))
#     #imageL2.paste(evenInput, (0,0))
#
#     oddOffset = positions[0][addr - 1]
#     evenOffset = positions[1][addr - 1]
#     for i in range(8):
#         if (1 << i) & lval:
#             if i % 2: # Even
#                 x = int(xPos/SPN - PRIMITIVEOFFSET)
#                 y = int(yPos/SPN) + (13 * (i/2)) * 4 + evenOffset * 4 + 2
#                 if matrix[x, y][1] == 50:
#                     matrix[x, y] = (255, 50, 50, 255)
#                 if matrix[x, y][0] == 50:
#                     matrix[x, y] = (50, 50, 50, 255)
#                 else: matrix[x, y] = (255, 50, 255, 255)
#
#             else:
#                 x = int((xPos)/SPN)
#                 y = int(yPos/SPN) + (13 * (i/2)) * 4 + oddOffset * 4
#                 if matrix[x, y][2] == 50:
#                     matrix[x, y] = (255, 50, 50, 255)
#                 if matrix[x, y][0] == 50:
#                     matrix[x, y] = (50, 50, 50, 255)
#                 else: matrix[x, y] = (255, 50, 255, 255)
#
#
#
#         if (1 << i) & rval:
#             if i % 2: # Even
#                 x = (xPos/SPN - HEADOFFSET - PRIMITIVEOFFSET)
#                 y = int(yPos/SPN) + (13 * (i/2)) * 4 + evenOffset * 4 + 2
#                 if matrix[x, y][1] == 50 or matrix[x, y][2] == 50:
#                     matrix[x, y] = (50, 50, 50, 255)
#                 else: matrix[x, y] = (50, 255, 255, 255)
#             else:
#                 x = ((xPos)/SPN - HEADOFFSET)
#                 y = int(yPos/SPN) + (13 * (i/2)) * 4 + oddOffset * 4
#                 if matrix[x, y][1] == 50 or matrix[x, y][2] == 50:
#                     matrix[x, y] = (50, 50, 50, 255)
#                 else: matrix[x, y] = (50, 255, 255, 255)
#
#

'''
Splits an input image into two images.
'''
def splitImageTwos(image):
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

    odd.save("odd.jpg");
    even.save("even.jpg");

    return (odd, even)


tempInitiate()
# main()
