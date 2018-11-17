import functools

from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QStatusBar
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5.QtCore import QTimer



valNumOfIntDigits = 7
valNumOfFracDigits = 3

MSG_TIMEOUT = 5000



class ErrorsSettingsWindow(QWidget):

    def __init__(self, app, parent=None):

        super(ErrorsSettingsWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle("PID errors settings")
        self.setWindowIcon(QIcon('img/set_errors.png'))


        self.lineEdits = {
            'PerrLimits': {
                'min': QLineEdit(),
                'max': QLineEdit()
            },
            'IerrLimits': {
                'min': QLineEdit(),
                'max': QLineEdit()
            }
        }

        for d in self.lineEdits.values():
            for lineEdit in d.values():
                lineEdit.setValidator(QDoubleValidator())


        PerrLimitsSetButton = QPushButton('Set')
        PerrLimitsSetButton.clicked.connect(functools.partial(self.setErrLimits, 'PerrLimits'))

        PerrHBox = QHBoxLayout()
        PerrHBox.addWidget(QLabel("Min:"))
        PerrHBox.addWidget(self.lineEdits['PerrLimits']['min'])
        PerrHBox.addWidget(QLabel("Max:"))
        PerrHBox.addWidget(self.lineEdits['PerrLimits']['max'])
        PerrHBox.addWidget(PerrLimitsSetButton)

        PerrGroupBox = QGroupBox("P error limits")
        PerrGroupBox.setLayout(PerrHBox)


        IerrLimitsSetButton = QPushButton('Set')
        IerrLimitsSetButton.clicked.connect(functools.partial(self.setErrLimits, 'IerrLimits'))

        resetIerrButton = QPushButton("Reset I error")
        resetIerrButton.clicked.connect(self.resetIerr)

        IerrHBox1 = QHBoxLayout()
        IerrHBox1.addWidget(QLabel("Min:"))
        IerrHBox1.addWidget(self.lineEdits['IerrLimits']['min'])
        IerrHBox1.addWidget(QLabel("Max:"))
        IerrHBox1.addWidget(self.lineEdits['IerrLimits']['max'])
        IerrHBox1.addWidget(IerrLimitsSetButton)

        IerrHBox2 = QHBoxLayout()
        IerrHBox2.addWidget(resetIerrButton)

        IerrVBox = QVBoxLayout()
        IerrVBox.addLayout(IerrHBox1)
        IerrVBox.addLayout(IerrHBox2)

        IerrGroupBox = QGroupBox("I error limits")
        IerrGroupBox.setLayout(IerrVBox)


        self.statusBar = QStatusBar()


        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(PerrGroupBox)
        grid.addWidget(IerrGroupBox)
        grid.addWidget(self.statusBar)


    def show(self):
        self.updateDisplayingValues('PerrLimits', 'IerrLimits')
        super(ErrorsSettingsWindow, self).show()


    def removeStatusBarWidget(self, widget):
        self.statusBar.removeWidget(widget)


    def updateDisplayingValues(self, *what):
        for item in what:
            valMin, valMax = self.app.conn.read(item)
            # TODO: maybe round in MCUconn
            self.lineEdits[item]['min'].setText(f'{round(valMin, valNumOfFracDigits)}')
            self.lineEdits[item]['max'].setText(f'{round(valMax, valNumOfFracDigits)}')


    def setErrLimits(self, what):
        try:
            valMin = float(self.lineEdits[what]['min'].text())
            valMax = float(self.lineEdits[what]['max'].text())
            if valMax < valMin:
                resultLabel = QLabel("<font color='red'>Upper limit value is less than lower!</font>")
            else:
                self.app.conn.write(what, valMin, valMax)
                resultLabel = QLabel("Success")
            self.statusBar.addWidget(resultLabel)
            QTimer().singleShot(MSG_TIMEOUT, functools.partial(self.removeStatusBarWidget, resultLabel))
        except ValueError:
            pass
        self.updateDisplayingValues(what)


    def resetIerr(self):
        self.app.conn.resetIerr()
        infoLabel = QLabel("Ierr has been reset")
        self.statusBar.addWidget(infoLabel)
        QTimer().singleShot(MSG_TIMEOUT, functools.partial(self.removeStatusBarWidget, infoLabel))
