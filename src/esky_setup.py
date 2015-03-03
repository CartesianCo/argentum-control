#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington
    Copyright (C) 2015 Michael Reed

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from esky.bdist_esky import Executable
from distutils.core import setup

from setup import APP, OPTIONS, BASEVERSION, VERSION, NAME

exe = Executable(APP)
DATA_FILES = ['tools/avrdude', 'avrdude.conf']

OPTIONS = {
    "bdist_esky": {
        "freezer_module": "py2app",
        "freezer_options": {
            'includes': [
                'PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui'
            ],
            'excludes': [
                'PyQt4.QtDesigner', 'PyQt4.QtNetwork', 'PyQt4.QtOpenGL',
                'PyQt4.QtScript', 'PyQt4.QtSql', 'PyQt4.QtTest',
                'PyQt4.QtWebKit', 'PyQt4.QtXml', 'PyQt4.phonon'
            ],

            'argv_emulation': True,
            'emulate-shell-environment': True,
            'iconfile': 'Icon.icns',
            'plist': 'Info.plist'
        }
    }
}


setup(
    name = NAME,
    description = 'Argentum Control Software',
    author = 'Cartesian Co.',
    author_email = 'software@cartesianco.com',
    url = 'http://www.cartesianco.com',
    #packages = [],
    options = OPTIONS,
    version = BASEVERSION,
    data_files = DATA_FILES,
    scripts = [exe]
)
