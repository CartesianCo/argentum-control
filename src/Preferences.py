#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Argentum Control GUI

    Copyright (C) 2013 Isabella Stevens
    Copyright (C) 2014 Michael Shiel
    Copyright (C) 2015 Trent Waddington

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

        self.pollForPos = QtGui.QCheckBox("Poll printer for position of print head")
        self.pollForPos.setChecked(True)
        mainLayout.addWidget(self.pollForPos)

        self.lightsAlwaysOn = QtGui.QCheckBox("Turn lights on when printer is connected")
        self.lightsAlwaysOn.setChecked(True)
        mainLayout.addWidget(self.lightsAlwaysOn)

        self.motorsStartOff = QtGui.QCheckBox("Start with motors off")
        self.motorsStartOff.setChecked(False)
        mainLayout.addWidget(self.motorsStartOff)

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
        self.read_setting("poll_for_pos", self.pollForPos)
        self.read_setting("lights_always_on", self.lightsAlwaysOn)
        self.read_setting("motors_start_off", self.motorsStartOff)

    def save(self):
        self.write_setting("autoconnect", self.autoConnect)
        self.write_setting("home_on_connect", self.homeOnConnect)
        self.write_setting("use_rollers", self.useRollers)
        self.write_setting("also_pause", self.alsoPause)
        self.write_setting("console_start", self.consoleStart)
        self.write_setting("poll_for_pos", self.pollForPos)
        self.write_setting("lights_always_on", self.lightsAlwaysOn)
        self.write_setting("motors_start_off", self.motorsStartOff)
        self.argentum.updateOptions(self.options)
        self.accept()

