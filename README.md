argentum-control
============

GUI Control Program for the Argentum Circuit Printer

This Python app uses a number of libraries that may not be installed by default on your system (especially if you're using Windows). Obviously you may need to install Python, the latest version should be fine and should include the package manager (pip). Next, install PyQt4 if installing Python does not install it automatically (for most platforms it does).

PyQt4 Windows installer: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyqt4

The remaining requirements can be installed with pip:

    pip install esky Pillow pyserial requests

Running this command may nag you to install developer tools. Do that and rerun the command.

At this point you're ready to run the program:

    cd src
    python gui.py

If you see an error message that requires you to install another package, please let someone know so this documentation can be updated.

