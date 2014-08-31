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
