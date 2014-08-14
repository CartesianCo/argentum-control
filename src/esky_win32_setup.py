from esky.bdist_esky import Executable
from distutils.core import setup

exe = Executable("gui.py")
DATA_FILES = ['avrdude', 'avrdude.conf']

setup(
    name = "Argentum",
    options = {"bdist_esky": {
		"freezer_module": "cxfreeze",
        "freezer_options": {
        	'includes': ['PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui'],
            'excludes': ['PyQt4.QtDesigner', 'PyQt4.QtNetwork', 'PyQt4.QtOpenGL', 'PyQt4.QtScript', 'PyQt4.QtSql', 'PyQt4.QtTest', 
            	'PyQt4.QtWebKit', 'PyQt4.QtXml', 'PyQt4.phonon']
         	}
     	}
 	},
	data_files=DATA_FILES,
    scripts=[exe]
)
