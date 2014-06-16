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
            layout = QtGui.QHBoxLayout()

            widget = self.createOptionWidget(layout, optionName, defaultValue)

            self.created[optionName] = widget

            parentLayout.addLayout(layout)

    def addLabel(self, layout, labelText):
        label = QtGui.QLabel()
        label.setText(labelText)
        layout.addWidget(label)

    def gatherValues(self):
        options = []

        for name, widget in self.created.items():
            option = {name: str(widget.text())}

            options.append(option)

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
