#!/usr/bin/python

import sys
import os
import math

class Gerber:
    color = "#272749"
    comments = []
    errors = []
    lines = []
    attributes = {}
    apertures = {}
    levels = []

    class Level:
        operations = []

        def __init__(self, polarity=None):
            self.polarity = polarity

    class Aperture:
        def __init__(self, name, args=None, attributes=None):
            self.name = name
            self.args = args
            self.attributes = attributes

        def width(self):
            return float(self.args[0])

        def toSVG(self, x, y):
            if self.name == "C":
                diameter = float(self.args[0])
                hole = float(self.args[1]) if len(self.args) > 1 else None
                return '<circle cx="{}" cy="{}" r="{}" fill="{}" />\n'.format(x, y, diameter/2, Gerber.color)
            elif self.name == "R":
                width = float(self.args[0])
                height = float(self.args[1])
                hole = float(self.args[2]) if len(self.args) > 2 else None
                return '<rect x="{}" y="{}" width="{}" height="{}" fill="{}" />\n'.format(x - width/2, y - height/2, width, height, Gerber.color)
            elif self.name == "O":
                width = float(self.args[0])
                height = float(self.args[1])
                hole = float(self.args[2]) if len(self.args) > 2 else None
                return "<!-- {}, {} unimplemented obround {} {} -->\n".format(x, y, width, height)
            elif self.name == "P":
                diameter = float(self.args[0])
                num_vertices = float(self.args[1])
                rotation = float(self.args[2]) if len(self.args) > 2 else None
                hole = float(self.args[3]) if len(self.args) > 3 else None
                return "<!-- {}, {} unimplemented polygon {} {} -->\n".format(x, y, diameter, num_vertices)
            else:
                return "<!-- {}, {} unimplemented macro {} -->\n".format(x, y, self.name)

    def parse(self, contents):
        cur_aperture_attributes = {}
        self.lines = contents.split('\n')
        lineno = 0
        for line in self.lines:
            lineno = lineno + 1
            line = line.rstrip()
            if line == '':
                continue
            if line[0:4] == 'G04 ':
                line = line[4:]
                if line[-1:] == '*':
                    line = line[:-1]
                else:
                    self.errors.append((lineno, "Unterminated comment"))
                self.comments.append((lineno, line))
            elif line[0] == '%':
                line = line[1:]
                if line[-1:] == '%':
                    line = line[:-1]
                else:
                    self.errors.append((lineno, "Unterminated parameter code"))

                code = line[0:2]
                modifiers = line[2:]

                # Graphics parameter codes
                if code == 'FS':
                    if modifiers[0] == 'L':
                        self.omitLeadingZeros = True
                        modifiers = modifiers[1:]
                    elif modifiers[0] == 'T':
                        self.omitTrailingZeros = True
                        modifiers = modifiers[1:]
                    if modifiers[0] == 'A':
                        self.absoluteNotation = True
                        modifiers = modifiers[1:]
                    elif modifiers[0] == 'I':
                        self.incrementalNotation = True
                        modifiers = modifiers[1:]
                    if modifiers[0] == 'X':
                        self.integerPositions = int(modifiers[1])
                        self.decimalPositions = int(modifiers[2])
                        modifiers = modifiers[3:]
                    else:
                        self.errors.append((lineno, "Invalid format specification"))
                    if modifiers[0] == 'Y':
                        integerPositions = int(modifiers[1])
                        decimalPositions = int(modifiers[2])
                        if integerPositions != self.integerPositions:
                            self.errors.append((lineno, "Invalid format specification"))
                        elif decimalPositions != self.decimalPositions:
                            self.errors.append((lineno, "Invalid format specification"))
                        modifiers = modifiers[3:]
                    else:
                        self.errors.append((lineno, "Invalid format specification"))
                    if modifiers != "*":
                        self.errors.append((lineno, "Unterminated format specification"))
                    continue
                if code == 'MO':
                    if modifiers == "IN*":
                        self.units = "inches"
                    elif modifiers == "MM*":
                        self.units = "millimeters"
                    else:
                        self.errors.append((lineno, "Invalid mode specification"))
                    continue
                if code == 'AD':
                    if modifiers[0] == 'D':
                        modifiers = modifiers[1:]
                    else:
                        self.errors.append((lineno, "Invalid aperture definition"))
                    if modifiers[-1:] == '*':
                        modifiers = modifiers[:-1]
                    else:
                        self.errors.append((lineno, "Unterminated aperture definition"))

                    dcodestr = ""
                    while modifiers[0] >= '0' and modifiers[0] <= '9':
                        dcodestr = dcodestr + modifiers[0]
                        modifiers = modifiers[1:]
                    dcode = int(dcodestr)

                    mods = modifiers.split(',')
                    name = mods[0]
                    args = mods[1].split('X')

                    aperture = self.Aperture(name, args, cur_aperture_attributes)
                    self.apertures[dcode] = aperture
                    continue
                if code == 'AM':
                    self.errors.append((lineno, "Aperture macros are not implemented"))
                    continue
                if code == 'SR':
                    if modifiers[-1:] == '*':
                        modifiers = modifiers[:-1]
                    else:
                        self.errors.append((lineno, "Unterminated step and repeat"))
                    if modifiers == '':
                        # This typically means "do the step"
                        continue

                    if modifiers[0] != 'X':
                        self.errors.append((lineno, "Invalid step and repeat"))
                        continue
                    modifiers = modifiers[1:]

                    xRepeatStr = ""
                    while modifiers[0] >= '0' and modifiers[0] <= '9':
                        xRepeatStr = xRepeatStr + modifiers[0]
                        modifiers = modifiers[1:]
                    xRepeat = int(xRepeatStr)

                    if modifiers[0] != 'Y':
                        self.errors.append((lineno, "Invalid step and repeat"))
                        continue
                    modifiers = modifiers[1:]

                    yRepeatStr = ""
                    while modifiers[0] >= '0' and modifiers[0] <= '9':
                        yRepeatStr = yRepeatStr + modifiers[0]
                        modifiers = modifiers[1:]
                    yRepeat = int(yRepeatStr)

                    if modifiers[0] != 'I':
                        self.errors.append((lineno, "Invalid step and repeat"))
                        continue
                    modifiers = modifiers[1:]

                    iStepStr = ""
                    while modifiers[0] >= '0' and modifiers[0] <= '9' or modifiers[0] == '.':
                        iStepStr = iStepStr + modifiers[0]
                        modifiers = modifiers[1:]
                    iStep = float(iStepStr)

                    if modifiers[0] != 'J':
                        self.errors.append((lineno, "Invalid step and repeat"))
                        continue
                    modifiers = modifiers[1:]

                    jStepStr = ""
                    while modifiers[0] >= '0' and modifiers[0] <= '9' or modifiers[0] == '.':
                        jStepStr = jStepStr + modifiers[0]
                        modifiers = modifiers[1:]
                        if modifiers == '':
                            break
                    jStep = float(jStepStr)

                    self.stepAndRepeat = (xRepeat, yRepeat, iStep, jStep)

                    if xRepeat != 1 or yRepeat != 1:
                        self.errors.append((lineno, "Unsupported step and repeat"))
                    continue
                if code == 'LP':
                    polarity = None
                    if modifiers == "C*":
                        polarity = "clear"
                    elif modifiers == "D*":
                        polarity = "dark"
                    else:
                        self.errors.append((lineno, "Invalid level polarity"))
                    self.levels.append(self.Level(polarity))
                    continue

                # File attributes
                if code == 'TF':
                    if modifiers[-1] == '*':
                        modifiers = modifiers[:-1]
                    else:
                        self.errors.append((lineno, "Unterminated file attributes"))
                    mods = modifiers.split(',')
                    attribute = mods[0]
                    mods = mods[1:]
                    self.attributes[attribute] = mods
                    continue

                # Aperture attributes
                if code == 'TA':
                    if modifiers[-1] == '*':
                        modifiers = modifiers[:-1]
                    else:
                        self.errors.append([lineno, "Untermined aperture attribute add"])
                    mods = modifiers.split(',')
                    attribute = mods[0]
                    mods = mods[1:]
                    cur_aperture_attributes[attribute] = mods
                    continue
                if code == 'TD':
                    if modifiers[-1] == '*':
                        modifiers = modifiers[:-1]
                    else:
                        self.errors.append([lineno, "Untermined aperture attribute del"])
                    del cur_aperture_attributes[modifiers]
                    continue

                self.errors.append((lineno, "Unknown parameter code"))
                continue
            else:
                if line[-1:] == '*':
                    line = line[:-1]
                else:
                    self.errors.append((lineno, "Unterminated function code"))

                operation = {"line": lineno}

                code = line[0:3]
                if code == 'G01':
                    operation["interpolate_mode"] = "linear"
                    line = line[3:]
                elif code == 'G02':
                    operation["interpolate_mode"] = "clockwise"
                    line = line[3:]
                elif code == 'G03':
                    operation["interpolate_mode"] = "counterclockwise"
                    line = line[3:]
                elif code == 'G36':
                    operation["region_mode"] = "on"
                    line = line[3:]
                elif code == 'G37':
                    operation["region_mode"] = "off"
                    line = line[3:]
                elif code == 'G74':
                    operation["quadrant_mode"] = "single"
                    line = line[3:]
                elif code == 'G75':
                    operation["quadrant_mode"] = "multi"
                    line = line[3:]
                else:
                    code = code[:2]
                    if code == 'G1':
                        operation["interpolate_mode"] = "linear"
                        line = line[2:]
                    elif code == 'G2':
                        operation["interpolate_mode"] = "clockwise"
                        line = line[2:]
                    elif code == 'G3':
                        operation["interpolate_mode"] = "counterclockwise"
                        line = line[2:]
                    elif code == 'G4':
                        operation["ignore"] = True
                        line = line[2:]

                coordinates = {}
                while (len(line) > 0 and
                          (line[0] == 'X' or line[0] == 'Y' or
                           line[0] == 'I' or line[0] == 'J')):
                    axis = line[0]
                    line = line[1:]
                    sgn = ""
                    valstr = ""
                    if line[0] == '-':
                        sgn = '-'
                        line = line[1:]
                    while line[0] >= '0' and line[0] <= '9':
                        valstr = valstr + line[0]
                        line = line[1:]
                    if self.omitLeadingZeros:
                        intstr = valstr[0:-self.decimalPositions]
                        decstr = valstr[-self.decimalPositions:]
                    else:
                        intstr = valstr[0:self.integerPositions]
                        decstr = valstr[self.integerPositions:]
                    val = float(intstr + "." + decstr)
                    if sgn == '-':
                        val = -val
                    coordinates[axis] = val

                if coordinates:
                    operation["coordinates"] = coordinates

                code = line
                if code == 'D01':
                    operation["action"] = "interpolate"
                elif code == 'D02':
                    operation["action"] = "move"
                elif code == 'D03':
                    operation["action"] = "flash"
                elif (len(code) > 0 and
                          code[0] == 'D' and
                          code[1] >= '1' and code[1] <= '9'
                      and code[2] >= '0' and code[2] <= '9'):
                    operation["action"] = "aperture"
                    operation["aperture"] = int(code[1:])
                elif code == 'M02':
                    operation["action"] = "end"
                elif code != '':
                    self.errors.append((lineno, "Unknown function code"))
                    continue

                if len(self.levels) == 0:
                    self.levels.append(self.Level())
                self.levels[-1].operations.append(operation)

    def path(self, d, stroke_width, region_mode):
        if region_mode:
            return '<path d="{}" fill="{}" />\n'.format(d, self.color)
        else:
            return '<path d="{}" fill="none" stroke="{}" stroke-width="{}" />\n'.format(d, self.color, stroke_width)

    def toSVG(self):
        stroke_width = 1

        width = 0
        height = 0

        body = ""
        for level in self.levels:
            d = ""
            X = 0
            Y = 0
            cur_aperture = None
            interpolate_mode = "linear"
            region_mode = False
            quadrant_mode = "single"
            for op in level.operations:
                #body = body + "<!-- line {} -->\n".format(op["line"])
                oldX = X
                oldY = Y
                I = 0
                J = 0
                if "coordinates" in op:
                    coordinates = op["coordinates"]
                    if "X" in coordinates:
                        X = coordinates["X"]
                        if X > width:
                            width = X
                    if "Y" in coordinates:
                        Y = coordinates["Y"]
                        if Y > height:
                            height = Y
                    if "I" in coordinates:
                        I = coordinates["I"]
                    if "J" in coordinates:
                        J = coordinates["J"]
                if "interpolate_mode" in op:
                    interpolate_mode = op["interpolate_mode"]
                if "region_mode" in op:
                    if op["region_mode"] == "on":
                        region_mode = True
                    else:
                        if d != "":
                            body = body + self.path(d, stroke_width, region_mode)
                            d = ""
                        region_mode = False
                if "quadrant_mode" in op:
                    quadrant_mode = op["quadrant_mode"]
                action = op["action"] if "action" in op else None
                if action == "move":
                    if d != "":
                        body = body + self.path(d, stroke_width, region_mode)
                    d = "M {} {}".format(X, Y)
                elif action == "interpolate":
                    if interpolate_mode == "linear":
                        d = d + " L {} {}".format(X, Y)
                    else:
                        cw = (interpolate_mode == "clockwise")
                        sx, sy = (oldX, oldY)
                        ex, ey = (X, Y)
                        cx, cy = (oldX + I, oldY + J)
                        r = math.sqrt(I*I + J*J)

                        thetaE = math.atan2(ey-cy, ex-cx)
                        if thetaE < 0:
                            thetaE = thetaE + math.pi*2
                        thetaS = math.atan2(sy-cy, sx-cx)
                        if thetaS < 0:
                            thetaS = thetaS + math.pi*2
                        if cw and thetaS < thetaE:
                            thetaS = thetaS + math.pi*2
                        elif not cw and thetaE < thetaS:
                            thetaE = thetaE + math.pi*2
                        theta = math.fabs(thetaE - thetaS)

                        laf = 0
                        if quadrant_mode == "multi" and theta >= math.pi:
                            laf = 1

                        sf = 0 if cw else 1

                        # Check for full circle
                        epsilon = 1.01*math.pow(10, -(self.decimalPositions-1))
                        if (quadrant_mode == "multi" and
                                math.fabs(sx-ex) < epsilon and
                                math.fabs(sy-ey) < epsilon):
                            d = d + " A {} {} {} {} {} {} {}".format(r, r, 0, 0, sf, ex+2*I, ey+2*J)

                        d = d + " A {} {} {} {} {} {} {}".format(r, r, 0, laf, sf, ex, ey)
                elif action == "aperture":
                    cur_aperture = self.apertures[op["aperture"]]
                    stroke_width = cur_aperture.width()
                elif action == "flash":
                    if d != "":
                        body = body + self.path(d, stroke_width, region_mode)
                        d = ""
                    body = body + cur_aperture.toSVG(X, Y)
            if d != "":
                body = body + self.path(d, stroke_width, region_mode)

        self.width = width
        self.height = height

        svg = '<?xml version="1.0" encoding="UTF-8"?>\n'
        svg = svg + '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        svg = svg + '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}" height="{}">\n'.format(width, height)
        svg = svg + '<g transform="translate(0 {}) scale(1 -1)">\n'.format(height)
        svg = svg + body
        svg = svg + '</g>\n'
        svg = svg + '</svg>\n'
        return svg

def main(args):
    if len(args) < 1:
        print("usage: gerber <gerber file>")
        sys.exit(1)

    f = open(args[0])
    contents = f.read()
    f.close()

    g = Gerber()
    g.parse(contents)
    if len(g.errors) > 0:
        for error in g.errors:
            lineno, msg = error
            sys.stderr.write("{}: {}\n".format(lineno, msg))
    print(g.toSVG())

    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
