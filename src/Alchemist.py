from PyQt4 import QtGui, QtCore

class OptionsDialog(QtGui.QDialog):
    '''
    Argentum Options Dialog
    '''

    created = {}

    def __init__(self, parent=None, options=None):

        QtGui.QWidget.__init__(self, parent)

        self.parent = parent
        self.options = options

        #--Layout Stuff---------------------------#
        mainLayout = QtGui.QVBoxLayout()

        if self.options:
            self.addOptions(mainLayout, self.options)

        #--The Button------------------------------#
        layout = QtGui.QHBoxLayout()
        button = QtGui.QPushButton("Save") #string or icon
        #self.connect(button, QtCore.SIGNAL("clicked()"), self.close)
        button.clicked.connect(self.gatherValues)
        layout.addWidget(button)

        mainLayout.addLayout(layout)
        self.setLayout(mainLayout)

        self.resize(400, 60)
        self.setWindowTitle('Printer Options')

    def createOptionWidget(self, parentLayout, optionName, defaultValue):
        # Create a Sub-Layout for this option
        #layout = QtGui.QHBoxLayout()

        self.addLabel(parentLayout, optionName)

        # Make sure it's a string with str(...)
        optionLineEdit = QtGui.QLineEdit(str(defaultValue))
        parentLayout.addWidget(optionLineEdit)

        return optionLineEdit

    def addOptions(self, parentLayout, options):
        for optionName, defaultValue in options.items():
            if optionName == "last_run":
                continue
            layout = QtGui.QHBoxLayout()

            widget = self.createOptionWidget(layout, optionName, defaultValue)

            self.created[optionName] = widget

            parentLayout.addLayout(layout)

    def addLabel(self, layout, labelText):
        label = QtGui.QLabel()
        label.setText(labelText)
        layout.addWidget(label)

    def gatherValues(self):
        options = {}

        for name, widget in self.created.items():
            options[name] = str(widget.text())

        self.parent.updateOptions(options)

        self.close()


class InputDialog(QtGui.QDialog):
   '''
   this is for when you need to get some user input text
   '''

   def __init__(self, parent=None, title='user input', label='comment', text=''):

       QtGui.QWidget.__init__(self, parent)

       #--Layout Stuff---------------------------#
       mainLayout = QtGui.QVBoxLayout()

       layout = QtGui.QHBoxLayout()
       self.label = QtGui.QLabel()
       self.label.setText(label)
       layout.addWidget(self.label)

       self.text = QtGui.QLineEdit(text)
       layout.addWidget(self.text)

       mainLayout.addLayout(layout)

       #--The Button------------------------------#
       layout = QtGui.QHBoxLayout()
       button = QtGui.QPushButton("okay") #string or icon
       #self.connect(button, QtCore.SIGNAL("clicked()"), self.close)
       button.clicked.connect(self.close)
       layout.addWidget(button)

       mainLayout.addLayout(layout)
       self.setLayout(mainLayout)

       self.resize(400, 60)
       self.setWindowTitle(title)


class CommandLineEdit(QtGui.QLineEdit):
    submit_keys = [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]

    # Order must be up, down
    arrow_keys = [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]

    command_history = []
    history_index = -1
    last_content = ''

    def __init__(self, *args):
        QtGui.QLineEdit.__init__(self, *args)

    def event(self, event):
        if (event.type() == QtCore.QEvent.KeyPress):
            key = event.key()

            if key in self.submit_keys:
                self.emit(QtCore.SIGNAL("enterPressed"))

                # We leave the signal catcher to call self.submit_command()

                return True

            if key in self.arrow_keys:
                if len(self.command_history) < 1:
                    return True

                if self.history_index < 0:
                    self.last_content = str(self.text())

                if key == self.arrow_keys[0]:
                    self.history_index = min(self.history_index + 1, len(self.command_history) - 1)
                else:
                    self.history_index = max(self.history_index - 1, -1)

                if self.history_index < 0:
                    command = self.last_content
                else:
                    command = self.command_history[self.history_index]

                self.setText(command)

                return True

        return QtGui.QLineEdit.event(self, event)

    def submit_command(self):
        command = str(self.text())

        self.history_index = -1
        self.command_history.insert(0,command)

        self.setText("")

class ServoCalibrationDialog(QtGui.QDialog):
    '''
    Servo Calibration Dialog
    '''

    def __init__(self, controller, parent=None):

        QtGui.QWidget.__init__(self, parent)

        self.controller = controller
        self.parent = parent

        #--Layout Stuff---------------------------#
        mainLayout = QtGui.QVBoxLayout()

        # Controls Here
        row = QtGui.QHBoxLayout()
        self.addButton(row, "Up ^", self.servoUp)
        self.addButton(row, "Set Deployed Position", self.setDeployedPosition)
        mainLayout.addLayout(row)

        row = QtGui.QHBoxLayout()
        self.addButton(row, "Down v", self.servoDown)
        self.addButton(row, "Set Retracted Position", self.setRetractedPosition)
        mainLayout.addLayout(row)

        #--The Button------------------------------#
        layout = QtGui.QHBoxLayout()
        button = QtGui.QPushButton("Done") #string or icon
        self.connect(button, QtCore.SIGNAL("clicked()"), self.close)

        layout.addWidget(button)

        mainLayout.addLayout(layout)
        self.setLayout(mainLayout)

        self.resize(200, 60)
        self.setWindowTitle('Servo Calibration')

        button.setFocus()

    def servoUp(self):
        if self.controller:
            self.controller.servocommand('+')

    def servoDown(self):
        if self.controller:
            self.controller.servocommand('-')

    def setRetractedPosition(self):
        if self.controller:
            self.controller.servocommand('R')

    def setDeployedPosition(self):
        if self.controller:
            self.controller.servocommand('D')

    def addButton(self, parent, label, function):
        button = QtGui.QPushButton(label) #string or icon
        self.connect(button, QtCore.SIGNAL("clicked()"), function)

        parent.addWidget(button)

    def createOptionWidget(self, parentLayout, optionName, defaultValue):
        # Create a Sub-Layout for this option
        #layout = QtGui.QHBoxLayout()

        # Make sure it's a string with str(...)
        optionLineEdit = QtGui.QLineEdit(str(defaultValue))
        parentLayout.addWidget(optionLineEdit)

        return optionLineEdit

    def addOptions(self, parentLayout, options):
        for optionName, defaultValue in options.items():
            layout = QtGui.QHBoxLayout()

            widget = self.createOptionWidget(layout, optionName, defaultValue)

            self.created[optionName] = widget

            parentLayout.addLayout(layout)
