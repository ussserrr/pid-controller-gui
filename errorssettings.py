import functools

from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QStatusBar
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5.QtCore import QTimer

import remotecontroller



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
            'err_P_limits': {
                'min': QLineEdit(),
                'max': QLineEdit()
            },
            'err_I_limits': {
                'min': QLineEdit(),
                'max': QLineEdit()
            }
        }

        for d in self.lineEdits.values():
            for lineEdit in d.values():
                lineEdit.setValidator(QDoubleValidator())


        pErrLimitsSetButton = QPushButton('Set')
        pErrLimitsSetButton.clicked.connect(functools.partial(self.setErrLimits, 'err_P_limits'))

        pErrHBox = QHBoxLayout()
        pErrHBox.addWidget(QLabel("Min:"))
        pErrHBox.addWidget(self.lineEdits['err_P_limits']['min'])
        pErrHBox.addWidget(QLabel("Max:"))
        pErrHBox.addWidget(self.lineEdits['err_P_limits']['max'])
        pErrHBox.addWidget(pErrLimitsSetButton)

        pErrGroupBox = QGroupBox("P error limits")
        pErrGroupBox.setLayout(pErrHBox)


        iErrLimitsSetButton = QPushButton('Set')
        iErrLimitsSetButton.clicked.connect(functools.partial(self.setErrLimits, 'err_I_limits'))

        iErrResetButton = QPushButton("Reset I error")
        iErrResetButton.clicked.connect(self.resetIerr)

        iErrHBox1 = QHBoxLayout()
        iErrHBox1.addWidget(QLabel("Min:"))
        iErrHBox1.addWidget(self.lineEdits['err_I_limits']['min'])
        iErrHBox1.addWidget(QLabel("Max:"))
        iErrHBox1.addWidget(self.lineEdits['err_I_limits']['max'])
        iErrHBox1.addWidget(iErrLimitsSetButton)

        iErrHBox2 = QHBoxLayout()
        iErrHBox2.addWidget(iErrResetButton)

        iErrVBox = QVBoxLayout()
        iErrVBox.addLayout(iErrHBox1)
        iErrVBox.addLayout(iErrHBox2)

        iErrGroupBox = QGroupBox("I error limits")
        iErrGroupBox.setLayout(iErrVBox)


        self.statusBar = QStatusBar()


        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(pErrGroupBox)
        grid.addWidget(iErrGroupBox)
        grid.addWidget(self.statusBar)


    def show(self):
        self.updateDisplayingValues('err_P_limits', 'err_I_limits')
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
        if self.app.conn.reset_i_err() == remotecontroller.result['ok']:
            statusLabel = QLabel("Ierr has been reset")
        else:
            statusLabel = QLabel("<font color='red'>Ierr reset error</font>")
        self.statusBar.addWidget(statusLabel)
        QTimer().singleShot(MSG_TIMEOUT, functools.partial(self.removeStatusBarWidget, statusLabel))
