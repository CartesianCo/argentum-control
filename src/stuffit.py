#!/usr/bin/python

import sys
import os
import zipfile
import glob
import platform
import shutil
import warnings
from ship import guessFilesToShip, files

if len(sys.argv) < 2:
    print("usage: stuffit.py <path to installed files>")
    sys.exit(1)

path = sys.argv[1]

guessFilesToShip()

def badInstall():
    print("Path doesn't seem to contain an installation.")
    sys.exit(1)

def writeToZip(zipPath, file, fnOverride=None):
    f = open(file, "r")
    contents = f.read()
    f.close()
    if fnOverride:
        file = fnOverride
    zf = zipfile.ZipFile(zipPath, "a")
    written = False
    for info in zf.infolist():
        if info.filename == file:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                zf.writestr(info, contents)
            written = True
            break
    if not written:
        zf.writestr(file, contents)
    zf.close()

def stuffMac():
    x86_64_dir = glob.glob(path + "/*-x86_64")
    if x86_64_dir == None:
        badInstall()
    resoucesDir = (path + "/" + x86_64_dir
                        + "/Argentum Control.app/Contents/Resources")

    if not os.path.exists(resourcesDir + "/gui.py"):
        badInstall()
    sitePackages = resourcesDir + "/lib/python2.7/site-packages.zip"
    if not os.path.exists(sitePackages):
        badInstall()

    for file in files:
        if not os.path.exists(file):
            print("skipped {}".format(file))
            continue
        if file == "gui.py" or not file.endswith(".py"):
            shutil.copy2(file, resourcesDir)
        else:
            writeToZip(sitePackages, file)

def stuffWindows():
    library = path + "/library.zip"
    if not os.path.exists(library):
        badInstall()

    for file in files:
        if not os.path.exists(file):
            print("skipped {}".format(file))
            continue
        if not file.endswith(".py"):
            shutil.copy2(file, path)
        elif file == "gui.py":
            writeToZip(library, file, "gui__main__.py")
        else:
            writeToZip(library, file)

def stuffLinux():
    for file in files:
        if not os.path.exists(file):
            print("skipped {}".format(file))
            continue
        shutil.copy2(file, path)

if platform.system() == "Windows":
    stuffWindows()
elif platform.system() == "Linux":
    stuffLinux()
elif platform.system() == "Darwin":
    stuffMac()
else:
    print("What platform is this?")
    sys.exit(1)

sys.exit(0)
