#!/usr/bin/python

import sys
import os
import math

class Gerber:

    def __init__(self):
        self.comments = []
        self.errors = []
        self.lines = []
        self.attributes = {}
        self.macros = {}
        self.apertures = {}
        self.levels = []

    class Printer:
        def debugLineNum(self, lineno):
            pass

        def circle(self, x, y, diameter, exposure=True, stroke_width=None):
            pass

        def rect(self, x, y, width, height, exposure=True):
            pass

        def obround(self, x, y, width, height, exposure=True):
            pass

        def line(self, x1, y1, x2, y2, width, exposure=True):
            pass

        def polygon(self, points, exposure=True):
            pass

        def vectorLine(self, x, y, width, sx, sy, ex, ey, rot, exposure=True):
            self.line(x + sx, y + sy, x + ex, y + ey, width)

        def centerLine(self, x, y, width, height, cx, cy, rot, exposure=True):
            x = x + cx
            y = y + cy
            self.rect(x - width/2, y - height/2, width, height)

        def lowerLeftLine(self, x, y, width, height, llx, lly, rot, exposure=True):
            self.rect(x + llx, y + lly, width, height)

        def regularPolygon(self, x, y, num_vertices, cx, cy, diameter, rot, exposure=True):
            start = rot * math.pi/180
            step = 2*math.pi / num_vertices
            r = diameter / 2
            points = []
            for i in range(num_vertices):
                px = r * math.cos(start + i*step)
                py = r * math.sin(start + i*step)
                if math.fabs(px) < 0.0000001:
                    px = 0
                if math.fabs(py) < 0.0000001:
                    py = 0
                points.append((x + px, y + py))
            self.polygon(points, exposure)

        def outline(self, x, y, points, rot, exposure=True):
            ppoints = []
            for p in points:
                px, py = p
                ppoints.append((x + px, y + py))
            self.polygon(ppoints, exposure)

        def moire(self, x, y, cx, cy, diameter, ring_thickness, ring_gap, ring_count, cross_thickness, cross_length, rot):
            self.vectorLine(x, y, cross_thickness, cx - cross_length/2, cy, cx + cross_length/2, cy, 0)
            self.vectorLine(x, y, cross_thickness, cx, cy - cross_length/2, cx, cy + cross_length/2, 0)
            n = 0
            r = diameter / 2
            while n < ring_count:
                if r < ring_thickness + ring_gap:
                    self.circle(x + cx, y + cy, r*2)
                    break
                self.circle(x + cx, y + cy, (r - ring_thickness / 2) * 2, stroke_width=ring_thickness)
                r = r - ring_thickness - ring_gap
                n = n + 1

        def thermal(self, x, y, cx, cy, outer_diameter, inner_diameter, gap_thickness, rot):
            stroke_width = (outer_diameter - inner_diameter) / 2
            r = outer_diameter - stroke_width
            d = []
            gr = math.asin(gap_thickness/2/r)
            theta = 0
            for i in range(4):
                dx = r * math.sin(theta + gr)
                dy = r * math.cos(theta + gr)
                d.append("M {} {}".format(x + cx + dx, y + cy + dy))
                theta = theta + math.pi/2
                dx = r * math.sin(theta - gr)
                dy = r * math.cos(theta - gr)
                d.append("A {} {} {} {} {} {} {}".format(r, r, 0, 0, 0, x + cx + dx, y + cy + dy))
            self.path(d, stroke_width, False)

        def path(self, data, stroke_width, region_mode):
            pass

    class StdoutPrinter(Printer):
        def debugLineNum(self, lineno):
            print("line {}".format(lineno))

        def circle(self, x, y, diameter, exposure=True, stroke_width=None):
            print("circle {} {} {} {} {}".format(x, y, diameter, exposure, stroke_width))

        def rect(self, x, y, width, height, exposure=True):
            print("rect {} {} {} {} {}".format(x, y, width, height, exposure))

        def obround(self, x, y, width, height, exposure=True):
            print("obround {} {} {} {} {}".format(x, y, width, height, exposure))

        def line(self, x1, y1, x2, y2, width, exposure=True):
            print("line {} {} {} {} {} {}".format(x1, y2, x2, y2, width, exposure))

        def polygon(self, points, exposure=True):
            print("polygon {} {}".format(points, exposure))

        def regularPolygon(self, x, y, num_vertices, cx, cy, diameter, rot, exposure=True):
            print("regularPolygon {} {} {} {} {} {} {} {}".format(x, y, num_vertices, cx, cy, diameter, rot, exposure))

        def vectorLine(self, x, y, width, sx, sy, ex, ey, rot, exposure=True):
            print("vectorLine {} {} {} {} {} {} {} {} {}".format(x, y, width, sx, sy, ex, ey, rot, exposure))

        def centerLine(self, x, y, width, height, cx, cy, rot, exposure=True):
            print("centerLine {} {} {} {} {} {} {} {}".format(x, y, width, height, cx, cy, rot, exposure))

        def lowerLeftLine(self, x, y, width, height, llx, lly, rot, exposure=True):
            print("lowerLeftLine {} {} {} {} {} {} {} {}".format(x, y, width, height, llx, lly, exposure))

        def outline(self, x, y, points, rot, exposure=True):
            print("outLine {} {} {} {} {}".format(x, y, points, rot, exposure))

        def moire(self, x, y, cx, cy, diameter, ring_thickness, ring_gap, ring_count, cross_thickness, cross_length, rot):
            print("moire {} {} {} {} {} {} {} {} {} {} {}".format(x, y, cx, cy, diameter, ring_thickness, ring_gap, ring_count, cross_thickness, cross_length, rot))

        def thermal(self, x, y, cx, cy, outer_diameter, inner_diameter, gap_thickness, rot):
            print("thermal {} {} {} {} {} {} {} {}".format(x, y, cx, cy, outer_diameter, inner_diameter, gap_thickness, rot))

        def path(self, data, stroke_width, region_mode):
            print("path {} {} {}".format(' '.join(data), stroke_width, region_mode))

        def moveTo(self, x, y):
            print("M {} {}".format(x, y))

        def lineTo(self, x, y, stroke_width):
            print("L {} {} {}".format(x, y, stroke_width))

    class ArgentumTranslator(Printer):
        # Converts to commands the printer can understand
        # @printer an ArgentumPrinter class
        def __init__(self, printer):
            self.printer = printer

        @staticmethod
        def mm_to_steps(x):
            return int(x * 80)

        # TODO filled shapes

        def line(self, x1, y1, x2, y2, width, exposure=True):
            self.printer.moveTo(self.mm_to_steps(x1), self.mm_to_steps(y1))
            self.printer.lineTo(self.mm_to_steps(x2), self.mm_to_steps(y2), width)

        def path(self, data, stroke_width, region_mode):
            if not region_mode:
                for cmd in data:
                    parts = cmd.split()
                    x = self.mm_to_steps(float(parts[1]))
                    y = self.mm_to_steps(float(parts[2]))
                    if parts[0] == "M":
                        self.printer.moveTo(x, y)
                    elif parts[0] == "L":
                        self.printer.lineTo(x, y, stroke_width)
                    else:
                        pass

    class SVGPrinter(Printer):
        color = "#272749"

        def __init__(self):
            self.body = ""
            self.debug = False

        def debugLineNum(self, lineno):
            if self.debug:
                self.body += "<!-- line {} -->\n".format(lineno)

        def circle(self, x, y, diameter, exposure=True, stroke_width=None):
            if stroke_width:
                self.body += '<circle cx="{}" cy="{}" r="{}" fill="none" stroke-width="{}" stroke="{}" />\n'.format(x, y, diameter/2, stroke_width, self.color)
            else:
                self.body += '<circle cx="{}" cy="{}" r="{}" fill="{}" />\n'.format(x, y, diameter/2, self.color)

        def rect(self, x, y, width, height, exposure=True):
            self.body += '<rect x="{}" y="{}" width="{}" height="{}" fill="{}" />\n'.format(x - width/2, y - height/2, width, height, self.color)

        def obround(self, x, y, width, height, exposure=True):
            self.body += '<rect x="{}" y="{}" width="{}" height="{}" rx="0.25" ry="0.25" fill="{}" />\n'.format(x - width/2, y - height/2, width, height, self.color)

        def line(self, x1, y1, x2, y2, width, exposure=True):
            self.body += '<line x1="{}" y1="{}" x2="{}" y2="{}" stroke-width="{}" stroke-linecap="butt" stroke="{}" />\n'.format(x1, y1, x2, y2, width, self.color)

        def polygon(self, points, exposure=True):
            str = ""
            for point in points:
                x, y = point
                if str != "":
                    str += " "
                str += "{},{}".format(x, y)
            self.body += '<polygon points="{}" fill="{}" />\n'.format(str, self.color)

        def path(self, data, stroke_width, region_mode):
            if region_mode:
                self.body += '<path d="{}" fill="{}" />\n'.format(' '.join(data), self.color)
            else:
                self.body += '<path d="{}" fill="none" stroke="{}" stroke-width="{}" />\n'.format(' '.join(data), self.color, stroke_width)

    class Level:
        def __init__(self, polarity=None):
            self.polarity = polarity
            self.operations = []

    class Aperture:
        def __init__(self, name, args=None, attributes=None):
            self.name = name
            self.args = args
            self.attributes = attributes

        def width(self):
            if self.name in "CROP":
                return float(self.args[0])
            return self.macro.width()

        def printTo(self, printer, x, y):
            if self.name == "C":
                diameter = float(self.args[0])
                hole = float(self.args[1]) if len(self.args) > 1 else None
                printer.circle(x, y, diameter)
            elif self.name == "R":
                width = float(self.args[0])
                height = float(self.args[1])
                hole = float(self.args[2]) if len(self.args) > 2 else None
                printer.rect(x, y, width, height)
            elif self.name == "O":
                width = float(self.args[0])
                height = float(self.args[1])
                hole = float(self.args[2]) if len(self.args) > 2 else None
                printer.obround(x, y, width, height)
            elif self.name == "P":
                diameter = float(self.args[0])
                num_vertices = int(self.args[1])
                rotation = float(self.args[2]) if len(self.args) > 2 else None
                hole = float(self.args[3]) if len(self.args) > 3 else None
                printer.regularPolygon(x, y, num_vertices, 0, 0, diameter, 0)
            else:
                self.macro.printTo(printer, x, y, self.args)

    class Macro:
        def __init__(self, name):
            self.name = name
            self.contents = []

        def width(self):
            return 0

        def append(self, def_or_prim):
            self.contents.append(def_or_prim)

        class Element:
            def evalArithExp(self, state, exp):
                if len(exp)==2 and exp[0]=='$' and exp[1]>='0' and exp[1]<='9':
                    return state["v" + exp[1]]

                if len(exp) > 1 and exp[0] == '(' and exp[1] == ')':
                    return self.evalArithExp(state, exp[1:-1])

                if exp.find('x') != -1:
                    parts = exp.split('x')
                    return (self.evalArithExp(state, parts[0]) *
                            self.evalArithExp(state, parts[1]))

                if exp.find('X') != -1:
                    # Deprecated
                    parts = exp.split('X')
                    return (self.evalArithExp(state, parts[0]) *
                            self.evalArithExp(state, parts[1]))

                if exp.find('/') != -1:
                    parts = exp.split('/')
                    return (self.evalArithExp(state, parts[0]) /
                            self.evalArithExp(state, parts[1]))

                if exp.find('+') != -1:
                    parts = exp.split('+')
                    return (self.evalArithExp(state, parts[0]) +
                            self.evalArithExp(state, parts[1]))

                if exp.find('-') != -1:
                    parts = exp.split('-')
                    if parts[0] == '':
                        return -self.evalArithExp(state, parts[1])
                    return (self.evalArithExp(state, parts[0]) -
                            self.evalArithExp(state, parts[1]))

                return float(exp)

        class VarDef(Element):
            def __init__(self, K, value):
                self.K = K
                self.value = value

            def eval(self, state):
                state["v" + self.K] = self.evalArithExp(self.value)
                return state

        class Primitive(Element):
            def __init__(self, name, modifiers):
                self.name = name
                self.modifiers = modifiers

            def printTo(self, printer, state):
                x = state["x"]
                y = state["y"]
                args = []
                for modifier in self.modifiers:
                    args.append(self.evalArithExp(state, modifier))
                if self.name == "1":
                    exposure = (args[0] == 1)
                    diameter = args[1]
                    cx = args[2]
                    cy = args[3]
                    printer.circle(x + cx, y + cy, diameter, exposure=exposure)
                elif self.name == "2" or self.name == "20":
                    exposure = (args[0] == 1)
                    width = args[1]
                    sx = args[2]
                    sy = args[3]
                    ex = args[4]
                    ey = args[5]
                    rot = args[6]
                    printer.vectorLine(x, y, width, sx, sy, ex, ey, rot, exposure=exposure)
                elif self.name == "21":
                    exposure = (args[0] == 1)
                    width = args[1]
                    height = args[2]
                    cx = args[3]
                    cy = args[4]
                    rot = args[5]
                    printer.centerLine(x, y, width, height, cx, cy, rot, exposure=exposure)
                elif self.name == "22":
                    exposure = (args[0] == 1)
                    width = args[1]
                    height = args[2]
                    llx = args[3]
                    lly = args[4]
                    rot = args[5]
                    printer.lowerLeftLine(x, y, width, height, llx, lly, rot, exposure=exposure)
                elif self.name == "4":
                    exposure = (args[0] == 1)
                    num_subsequent_points = int(args[1])
                    sx = args[2]
                    sy = args[3]
                    points = [(sx, sy)]
                    for i in range(num_subsequent_points):
                        points.append((args[4 + i*2], args[4 + i*2 + 1]))
                    rot = args[4 + num_subsequent_points*2]
                    printer.outline(x, y, points, rot, exposure=exposure)
                elif self.name == "5":
                    exposure = (args[0] == 1)
                    num_vertices = args[1]
                    cx = args[2]
                    cy = args[3]
                    diameter = args[4]
                    rot = args[5]
                    printer.regularPolygon(x, y, num_vertices, cx, cy, diameter, rot, exposure=exposure)
                elif self.name == "6":
                    cx = args[0]
                    cy = args[1]
                    diameter = args[2]
                    ring_thickness = args[3]
                    ring_gap = args[4]
                    ring_count = args[5]
                    cross_thickness = args[6]
                    cross_length = args[7]
                    rot = args[8]
                    printer.moire(x, y, cx, cy, diameter, ring_thickness, ring_gap, ring_count, cross_thickness, cross_length, rot)
                elif self.name == "7":
                    cx = args[0]
                    cy = args[1]
                    outer_diameter = args[2]
                    inner_diameter = args[3]
                    gap_thickness = args[4]
                    rot = args[5]
                    printer.thermal(x, y, cx, cy, outer_diameter, inner_diameter, gap_thickness, rot)
                else:
                    pass #svg = svg + "<!-- {}, {} unknown prim {} in macro -->\n".format(state["x"], state["y"], self.name)
                return state

        def printTo(self, printer, x, y, args):
            state = {"x": x, "y": y}
            if args:
                for i in range(len(args)):
                    state["v{}".format(i+1)] = float(args[i])
            for elem in self.contents:
                state = elem.printTo(printer, state)

    def parse(self, contents):
        cur_aperture_attributes = {}
        self.lines = contents.split('\n')
        altlines = contents.split('\r')
        if len(self.lines) == 1 and len(altlines) > 1:
            self.lines = altlines
        lineno = 0
        skip = 0
        for line in self.lines:
            lineno = lineno + 1
            if skip > 0:
                skip = skip - 1
                continue
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
                while line[-1] != '%':
                    line = line + self.lines[lineno + skip].rstrip()
                    skip = skip + 1
                if line[-1] == '%':
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
                    args = mods[1].split('X') if len(mods) > 1 else None

                    aperture = self.Aperture(name, args, cur_aperture_attributes)
                    if not name in "CROP":
                        aperture.macro = self.macros[name]
                    self.apertures[dcode] = aperture

                    operation = {"action": "aperture", "aperture": dcode}
                    if len(self.levels) == 0:
                        self.levels.append(self.Level())
                    self.levels[-1].operations.append(operation)
                    continue
                if code == 'AM':
                    content = line[2:].split('*')
                    name = content[0]
                    m = self.Macro(name)
                    self.macros[name] = m
                    content = content[1:]
                    for def_or_prim in content:
                        if def_or_prim == '':
                            continue
                        if def_or_prim[0] == '$' and def_or_prim[2] == '=':
                            d = self.Macro.VarDef(def_or_prim[1], def_or_prim[3:])
                            m.append(d)
                        else:
                            prim = def_or_prim
                            if prim[0] == '0':
                                # throw away comments
                                continue
                            modifiers = prim.split(',')
                            name = modifiers[0]
                            modifiers = modifiers[1:]
                            p = self.Macro.Primitive(name, modifiers)
                            m.append(p)
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

                # Deprecared parameter codes
                if code == 'AS':
                    continue
                elif code == 'IN':
                    continue
                elif code == 'IP':
                    continue
                elif code == 'IR':
                    continue
                elif code == 'MI':
                    continue
                elif code == 'OF':
                    continue
                elif code == 'SF':
                    continue
                elif code == 'LN':
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
                elif (code == 'G54' or code == 'G55' or
                      code == 'G90' or code == 'G91' or
                      code == 'M00' or code == 'M01'):
                    # Deprecated and superfluous
                    line = line[3:]
                elif code == 'G70':
                    # Deprecated
                    self.units = "inches"
                    line = line[3:]
                elif code == 'G71':
                    # Deprecated
                    line = line[3:]
                    self.units = "millimeters"
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

    def printTo(self, printer, x=0, y=0):
        stroke_width = 1

        width = 0
        height = 0
        X = 0
        Y = 0
        cur_aperture = None
        interpolate_mode = "linear"
        region_mode = False
        quadrant_mode = "single"

        for level in self.levels:
            d = []
            for op in level.operations:
                if "line" in op:
                    printer.debugLineNum(op["line"])
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
                        if len(d) > 0:
                            printer.path(d, stroke_width, region_mode)
                            d = []
                        region_mode = False
                if "quadrant_mode" in op:
                    quadrant_mode = op["quadrant_mode"]
                action = op["action"] if "action" in op else None
                if action == "move":
                    if len(d) > 0:
                        printer.path(d, stroke_width, region_mode)
                    d = ["M {} {}".format(x + X, y + Y)]
                elif action == "interpolate":
                    if interpolate_mode == "linear":
                        d.append("L {} {}".format(x + X, y + Y))
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
                            d.append("A {} {} {} {} {} {} {}".format(r, r, 0, 0, sf, x+ex+2*I, y+ey+2*J))

                        d.append("A {} {} {} {} {} {} {}".format(r, r, 0, laf, sf, x+ex, y+ey))
                elif action == "aperture":
                    cur_aperture = self.apertures[op["aperture"]]
                    stroke_width = cur_aperture.width()
                elif action == "flash":
                    if len(d) > 0:
                        printer.path(d, stroke_width, region_mode)
                        d = []
                    cur_aperture.printTo(printer, x + X, y + Y)
            if len(d) > 0:
                printer.path(d, stroke_width, region_mode)

        self.width = width
        self.height = height

    def toSVG(self):
        printer = Gerber.SVGPrinter()
        self.printTo(printer)
        svg = '<?xml version="1.0" encoding="UTF-8"?>\n'
        svg = svg + '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        svg = svg + '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}" height="{}">\n'.format(self.width, self.height)
        svg = svg + '<g transform="translate(0 {}) scale(1 -1)">\n'.format(self.height)
        svg = svg + printer.body
        svg = svg + '</g>\n'
        svg = svg + '</svg>\n'
        return svg

def main(args):
    if len(args) < 1:
        print("usage: gerber [-s | -d] <gerber file>")
        sys.exit(1)

    svg = False
    debug = False
    if args[0] == '-s':
        svg = True
        args = args[1:]
    elif args[0] == '-d':
        debug = True
        args = args[1:]

    f = open(args[0])
    contents = f.read()
    f.close()

    g = Gerber()
    g.parse(contents)
    if len(g.errors) > 0:
        for error in g.errors:
            lineno, msg = error
            sys.stderr.write("{}: {}\n".format(lineno, msg))
    if svg:
        print(g.toSVG())
    elif debug:
        g.printTo(Gerber.StdoutPrinter())
    else:
        g.printTo(Gerber.ArgentumTranslator(Gerber.StdoutPrinter()))

    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
