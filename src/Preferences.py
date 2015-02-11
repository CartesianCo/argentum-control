
from PyQt4 import QtGui, QtCore
import pickle

class PreferencesDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.argentum = parent
        self.setWindowTitle("Preferences")
        mainLayout = QtGui.QVBoxLayout()

        self.autoConnect = QtGui.QCheckBox("Automatically connect to printer")
        self.autoConnect.setChecked(True)
        mainLayout.addWidget(self.autoConnect)

        self.homeOnConnect = QtGui.QCheckBox("Home printer on connect")
        self.homeOnConnect.setChecked(True)
        mainLayout.addWidget(self.homeOnConnect)

        self.useRollers = QtGui.QCheckBox("Use rollers to dry print")
        self.useRollers.setChecked(True)
        mainLayout.addWidget(self.useRollers)

        self.alsoPause = QtGui.QCheckBox("Pause after each print pass")
        self.alsoPause.setChecked(False)
        mainLayout.addWidget(self.alsoPause)

        self.consoleStart = QtGui.QCheckBox("Show console at startup")
        self.consoleStart.setChecked(False)
        mainLayout.addWidget(self.consoleStart)

        layout = QtGui.QHBoxLayout()
        cancelButton = QtGui.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton)
        self.saveButton = QtGui.QPushButton("Save")
        self.saveButton.clicked.connect(self.save)
        layout.addWidget(self.saveButton)
        mainLayout.addLayout(layout)

        self.saveButton.setDefault(True)

        self.setLayout(mainLayout)

        self.setup()

    def read_setting(self, name, check):
        try:
            if self.options[name] != check.isChecked():
                check.setChecked(self.options[name])
        except:
            pass

    def write_setting(self, name, check):
        self.options[name] = check.isChecked()

    def setup(self):
        self.options = self.argentum.options
        self.read_setting("autoconnect", self.autoConnect)
        self.read_setting("home_on_connect", self.homeOnConnect)
        self.read_setting("use_rollers", self.useRollers)
        self.read_setting("also_pause", self.alsoPause)
        self.read_setting("console_start", self.consoleStart)

    def save(self):
        self.write_setting("autoconnect", self.autoConnect)
        self.write_setting("home_on_connect", self.homeOnConnect)
        self.write_setting("use_rollers", self.useRollers)
        self.write_setting("also_pause", self.alsoPause)
        self.write_setting("console_start", self.consoleStart)
        self.argentum.updateOptions(self.options)
        self.accept()

