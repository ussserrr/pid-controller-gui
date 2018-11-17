import functools

from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QStatusBar
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

from miscgraphics import MessageWindow


valNumOfIntDigits = 7
valNumOfFracDigits = 3



class ErrorsSettingsWindow(QWidget):

    def __init__(self, app, parent=None):

        super(ErrorsSettingsWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle("PID errors settings")
        self.setWindowIcon(QIcon('img/set_errors.png'))


        # self.lineEdits = {'PerrLimits': QLineEdit(), 'IerrLimits': QLineEdit}


        # self.PerrMin, self.PerrMax = self.app.conn.read('PerrLimits')
        self.PerrMinLineEdit = QLineEdit()
        # self.PerrMinLineEdit.setText(f'{self.PerrMin}')
        self.PerrMaxLineEdit = QLineEdit()
        # self.PerrMaxLineEdit.setText(f'{self.PerrMax}')

        PerrLimitsSetButton = QPushButton('Set')
        PerrLimitsSetButton.clicked.connect(self.setPerrLimits)

        PerrHBox = QHBoxLayout()
        PerrHBox.addWidget(QLabel("Min:"))
        PerrHBox.addWidget(self.PerrMinLineEdit)
        PerrHBox.addWidget(QLabel("Max:"))
        PerrHBox.addWidget(self.PerrMaxLineEdit)
        PerrHBox.addWidget(PerrLimitsSetButton)

        PerrGroupBox = QGroupBox("P error limits")
        PerrGroupBox.setLayout(PerrHBox)


        # self.IerrMin, self.IerrMax = self.app.conn.read('IerrLimits')
        self.IerrMinLineEdit = QLineEdit()
        # self.IerrMinLineEdit.setText('{}'.format(self.IerrMin))
        self.IerrMaxLineEdit = QLineEdit()
        # self.IerrMaxLineEdit.setText('{}'.format(self.IerrMax))
        IerrLimitsSetButton = QPushButton('Set')
        IerrLimitsSetButton.clicked.connect(self.setIerrLimits)

        resetIerrButton = QPushButton("Reset I error")
        resetIerrButton.clicked.connect(self.resetIerr)

        IerrHBox1 = QHBoxLayout()
        IerrHBox1.addWidget(QLabel("Min:"))
        IerrHBox1.addWidget(self.IerrMinLineEdit)
        IerrHBox1.addWidget(QLabel("Max:"))
        IerrHBox1.addWidget(self.IerrMaxLineEdit)
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
        self.updateDisplayingValues('both')
        super(ErrorsSettingsWindow, self).show()


    def removeStatusBarWidget(self, widget):
        self.statusBar.removeWidget(widget)


    def updateDisplayingValues(self, what):
        if what == 'PerrLimits' or what == 'both':
            PerrMin, PerrMax = self.app.conn.read('PerrLimits')
            # TODO: maybe round in MCUconn
            self.PerrMinLineEdit.setText(f'{round(PerrMin, valNumOfFracDigits)}')
            self.PerrMaxLineEdit.setText(f'{round(PerrMax, valNumOfFracDigits)}')
        if what == 'IerrLimits' or what == 'both':
            IerrMin, IerrMax = self.app.conn.read('IerrLimits')
            self.IerrMinLineEdit.setText(f'{round(IerrMin, valNumOfFracDigits)}')
            self.IerrMaxLineEdit.setText(f'{round(IerrMax, valNumOfFracDigits)}')


    # def setErrLimits(self, what):
    #     try:
    #         warn = False
    #         if what == 'PerrLimits':
    #             if float(self.PerrMaxLineEdit.text()) < float(self.PerrMinLineEdit.text()):
    #                 warn = True
    #         elif what == 'IerrLimits':
    #             if float(self.IerrMaxLineEdit.text()) < float(self.IerrMinLineEdit.text()):
    #                 warn = True



    def setPerrLimits(self):
        try:
            if float(self.PerrMaxLineEdit.text()) < float(self.PerrMinLineEdit.text()):
                warnLabel = QLabel("<font color='red'>Upper limit value is less than lower!</font>")
                self.statusBar.addWidget(warnLabel)
                QTimer().singleShot(5000, functools.partial(self.removeStatusBarWidget, warnLabel))
            else:
                self.app.conn.write('PerrLimits', float(self.PerrMinLineEdit.text()), float(self.PerrMaxLineEdit.text()))
        except ValueError:
            pass
        self.updateDisplayingValues('PerrLimits')


    def setIerrLimits(self):
        try:
            if float(self.IerrMaxLineEdit.text()) < float(self.IerrMinLineEdit.text()):
                MessageWindow(text="Upper limit value is less than lower!", type='Error')
            else:
                self.app.conn.write('IerrLimits', float(self.IerrMinLineEdit.text()), float(self.IerrMaxLineEdit.text()))
        except ValueError:
            pass
        self.updateDisplayingValues('IerrLimits')


    def resetIerr(self):
        self.app.conn.resetIerr()
        self.statusBar.showMessage("Ierr has been reset", msecs=5000)
        # MessageWindow(text='Success. Current I-error: {}'.format(self.app.conn.read('Ierr')[0]), type='Info')
