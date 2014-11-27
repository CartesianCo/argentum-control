#!/usr/bin/python

import os
import sys
import tempfile
import shutil
import time
from setup import BASEVERSION

nightly = False
for opt in sys.argv[1:]:
    if opt == "--nightly":
        nightly = True

build = os.path.abspath("../../build")
build_out = build + "/" + BASEVERSION
_version = BASEVERSION.replace('.', '_')
firmware_file = "argentum_{}.hex".format(_version)
files = []

if nightly:
    build_out = build_out + "-nightly+" + time.strftime('%Y%m%d')
    _version = _version + "_nightly_" + time.strftime('%Y%m%d')

def makeBuildOut():
    print("Output will be in {}.".format(build_out))
    if os.path.isdir(build_out):
        print("Path already exists.")
        return
    os.system("mkdir {}".format(build_out))

def makeFirmware():
    if os.path.exists(firmware_file):
        print("Using existing firmware file.")
        shutil.copy2(firmware_file, build_out)
        return
    firmwarePath = "../../argentum-firmware/.build/mega2560/firmware.hex"
    if not os.path.exists(firmwarePath):
        print("You need to go build the firmware.")
        sys.exit(1)
    file = open(firmwarePath[:-4] + ".elf", "rb")
    contents = file.read()
    file.close()
    tofind = BASEVERSION + "+2014"
    if nightly:
        tofind = BASEVERSION + "-nightly+2014"
    if contents.find(tofind) == -1:
        print("You need to set the version number of the firmware.")
        if contents.find("+2014") == -1:
            print("Doesn't seem to have any version.")
        else:
            i = contents.find("+2014") - 1
            e = i + 5 + 4
            while contents[i] >= '0' and contents[i] <= '0' or contents[i] == '.':
                i = i - 1
            print("Seems to be {}.".format(contents[i:e]))
        sys.exit(1)
    shutil.copy2(firmwarePath, firmware_file)
    shutil.copy2(firmware_file, build_out)

def addDep(filename):
    if filename in files:
        return
    files.append(filename)
    file = open(filename, "r")
    contents = file.read()
    file.close()

    for line in contents.split('\n'):
        dep = None

        if line.find('from ') != -1:
            dep = line[line.find('from ')+5:]
            dep = dep[:dep.find(' ')]
        elif line.find('import ') != -1:
            dep = line[line.find('import ')+7:]
        elif line.find('QSvgRenderer(') != -1:
            svg = line[line.find('QSvgRenderer('):]
            if svg.find('"') != -1:
                svg = svg[svg.find('"')+1:]
                svg = svg[:svg.find('"')]
                files.append(svg)
            elif svg.find("'") != -1:
                svg = svg[svg.find("'")+1:]
                svg = svg[:svg.find("'")]
                files.append(svg)

        if dep and os.path.exists(dep + ".py"):
            addDep(dep + ".py")

def guessFilesToShip():
    addDep("gui.py")
    files.append(firmware_file)
    print("Packaging {} files.".format(len(files)))

def makeMacRelease():
    print("Making the Mac release...")
    os_x_app_template = build + "/os-x-app-template.tar.gz"
    if not os.path.exists(os_x_app_template):
        print("can't find " + os_x_app_template)
        return
    tmp = tempfile.mkdtemp()
    if not tmp or len(tmp) < 3:
        print("unable to make temp dir!")
        return
    os.system("tar -xzf {} --directory={}".format(os_x_app_template, tmp))

    siteFiles = []
    resources = []
    for file in files:
        if file[-3:] == ".py" and file != "gui.py":
            siteFiles.append(file)
        else:
            resources.append(file)

    resourceDir = tmp + "/Argentum Control.app/Argentum Control-0.0.6.macosx-10_9-x86_64/Argentum Control.app/Contents/Resources/"
    sitePackagesDir = resourceDir + "lib/python2.7/site-packages"
    for file in siteFiles:
        shutil.copy2(file, sitePackagesDir)
    for file in resources:
        shutil.copy2(file, resourceDir)

    cwd = os.getcwd()
    os.chdir(sitePackagesDir)
    os.system("zip -qr ../site-packages.zip ./")
    os.chdir(tmp + "/Argentum Control.app")
    shutil.rmtree(sitePackagesDir)

    os.chdir(tmp + "/Argentum Control.app/Contents")
    f = open("Info.plist", "r")
    plist = f.read()
    f.close()
    f = open("Info.plist", "w")
    for line in plist.split('\n'):
        if line == "\t<string>0.0.6</string>":
            line = "\t<string>{}</string>".format(BASEVERSION)
        f.write(line + "\n")
    f.close()

    os.chdir(tmp + "/Argentum Control.app")
    os.system("mv Argentum\ Control-0.0.6.macosx-10_9-x86_64 Argentum\ Control-{}.macosx-10_9-x86_64".format(BASEVERSION))

    os.chdir(tmp)
    outputFile = "Argentum-Control-{}-macosx-10_9-x86_64.zip".format(_version)
    os.system("zip -qr {} Argentum\\ Control.app".format(outputFile))
    os.system("mv {} {}/".format(outputFile, build_out))
    os.chdir(cwd)

    shutil.rmtree(tmp)

def makeWin32Release():
    print("Making the Win32 release...")
    win32_app_template = build + "/win32-app-template.tar.gz"
    if not os.path.exists(win32_app_template):
        print("can't find " + win32_app_template)
        return
    tmp = tempfile.mkdtemp()
    if not tmp or len(tmp) < 3:
        print("unable to make temp dir!")
        return
    os.system("tar -xzf {} --directory={}".format(win32_app_template, tmp))

    siteFiles = []
    resources = []
    for file in files:
        if file[-3:] == ".py":
            siteFiles.append(file)
        else:
            resources.append(file)

    resourceDir = tmp + "/Argentum Control-0.0.6.win32/"
    sitePackagesDir = resourceDir + "library"
    for file in siteFiles:
        if file == "gui.py":
            shutil.copy2(file, sitePackagesDir + "/gui__main__.py")
        else:
            shutil.copy2(file, sitePackagesDir)
    for file in resources:
        shutil.copy2(file, resourceDir)

    cwd = os.getcwd()
    os.chdir(sitePackagesDir)
    os.system("zip -qr ../library.zip ./")
    os.chdir(tmp)
    shutil.rmtree(sitePackagesDir)
    os.system("mv Argentum\ Control-0.0.6.win32 Argentum\ Control-{}.win32".format(BASEVERSION))

    os.chdir(tmp)
    outputFile = "Argentum-Control-{}-win32.zip".format(_version)
    os.system("zip -qry {} Argentum\\ Control-{}.win32".format(outputFile, BASEVERSION))
    os.system("mv {} {}/".format(outputFile, build_out))
    os.chdir(cwd)

    shutil.rmtree(tmp)

def makeLinuxRelease():
    print("Making the Linux release...")
    linux_app_template = build + "/linux-app-template.tar.gz"
    if not os.path.exists(linux_app_template):
        print("can't find " + linux_app_template)
        return
    tmp = tempfile.mkdtemp()
    if not tmp or len(tmp) < 3:
        print("unable to make temp dir!")
        return
    os.system("tar -xzf {} --directory={}".format(linux_app_template, tmp))

    cwd = os.getcwd()
    resourceDir = tmp + "/Argentum-Control-0.0.6.linux/"
    for file in files:
        shutil.copy2(file, resourceDir)

    os.chdir(tmp)
    os.system("mv Argentum-Control-0.0.6.linux Argentum-Control-{}.linux".format(BASEVERSION))

    outputFile = "Argentum-Control-{}-linux.tar.gz".format(_version)
    os.system("tar -czf {} Argentum-Control-{}.linux".format(outputFile, BASEVERSION))
    os.system("mv {} {}/".format(outputFile, build_out))
    os.chdir(cwd)

    shutil.rmtree(tmp)

if __name__ == '__main__':
    print("Version {}.".format(BASEVERSION))
    makeBuildOut()
    makeFirmware()
    guessFilesToShip()
    makeMacRelease()
    makeWin32Release()
    makeLinuxRelease()
