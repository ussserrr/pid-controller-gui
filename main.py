if __name__ == '__main__':
    print('loading...\n')
    __version__ = 'zeta'

import sys
from numpy import mean as numpy_mean, __version__ as numpy___version__
from time import time as time_time
from matplotlib import __version__ as matplotlib___version__

from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,\
                            QApplication, QSpinBox, QStatusBar, QProgressBar, QLineEdit, QCheckBox, QGridLayout,\
                            QTabWidget, QMainWindow, QToolTip, QAction, QLayout, QSizePolicy
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QCoreApplication, QSettings, Qt, QT_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR

from miscgraphics import PicButton, MessageWindow, Graph
from mcuconn import MCUconn



class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super(SettingsWindow, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon('img/settings.png'))

        self.onlyUGraphRadioButton = QRadioButton("Plot only U(t) graph")
        self.onlyPIDGraphRadioButton = QRadioButton("Plot only PID-output(t) graph")
        self.bothGraphsRadioButton = QRadioButton("Plot both graphs concurrently")
        self.onlyUGraphRadioButton.setChecked(True)

        chooseNumberOfGraphsVBox = QVBoxLayout()
        chooseNumberOfGraphsVBox.addWidget(self.onlyUGraphRadioButton)
        chooseNumberOfGraphsVBox.addWidget(self.onlyPIDGraphRadioButton)
        chooseNumberOfGraphsVBox.addWidget(self.bothGraphsRadioButton)
        chooseNumberOfGraphsGroupBox = QGroupBox("Graphs to plot:")
        chooseNumberOfGraphsGroupBox.setLayout(chooseNumberOfGraphsVBox)

        restoreLabel = QLabel("Restore all MCU values to values at program start time")
        restoreButton = QPushButton("Restore")
        restoreButton.clicked.connect(self.restore)

        saveToEEPROMLabel = QLabel("Save current PID configuration to EEPROM")
        saveToEEPROMButton = QPushButton("Save")
        saveToEEPROMButton.clicked.connect(self.saveToEEPROM)

        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(chooseNumberOfGraphsGroupBox)
        grid.addWidget(restoreLabel)
        grid.addWidget(restoreButton)
        grid.addWidget(saveToEEPROMLabel)
        grid.addWidget(saveToEEPROMButton)


    def restore(self):
        tivaConn.restoreValues()
        refreshAllPIDvalues()

    def saveToEEPROM(self):
        if not tivaConn.saveToEEPROM():
            MessageWindow(text='Successfully saved', type='Info')
            refreshAllPIDvalues()
        else:
            MessageWindow(text='Saving failed!', type='Warning')



class ErrorsSettingsWindow(QWidget):
    def __init__(self, parent=None):
        super(ErrorsSettingsWindow, self).__init__(parent)
        self.setWindowTitle("PID errors settings")
        self.setWindowIcon(QIcon('img/set_errors.png'))


        self.PerrMin, self.PerrMax = tivaConn.read('PerrLimits')
        PerrMinLabel = QLabel("Min:")
        self.PerrMinLineEdit = QLineEdit()
        self.PerrMinLineEdit.setText('{}'.format(self.PerrMin))
        PerrMaxLabel = QLabel("Max:")
        self.PerrMaxLineEdit = QLineEdit()
        self.PerrMaxLineEdit.setText('{}'.format(self.PerrMax))
        PerrLimitsSetButton = QPushButton('Set')
        PerrLimitsSetButton.clicked.connect(self.setPerrLimits)

        hPerrBox = QHBoxLayout()
        hPerrBox.addWidget(PerrMinLabel)
        hPerrBox.addWidget(self.PerrMinLineEdit)
        hPerrBox.addWidget(PerrMaxLabel)
        hPerrBox.addWidget(self.PerrMaxLineEdit)
        hPerrBox.addWidget(PerrLimitsSetButton)

        PerrGroupBox = QGroupBox("Set P error limits")
        PerrGroupBox.setLayout(hPerrBox)


        self.IerrMin, self.IerrMax = tivaConn.read('IerrLimits')
        IerrMinLabel = QLabel("Min:")
        self.IerrMinLineEdit = QLineEdit()
        self.IerrMinLineEdit.setText('{}'.format(self.IerrMin))
        IerrMaxLabel = QLabel("Max:")
        self.IerrMaxLineEdit = QLineEdit()
        self.IerrMaxLineEdit.setText('{}'.format(self.IerrMax))
        IerrLimitsSetButton = QPushButton('Set')
        IerrLimitsSetButton.clicked.connect(self.setIerrLimits)

        resetIerrButton = QPushButton("Reset I error")
        resetIerrButton.clicked.connect(self.resetIerr)

        hIerrBox1 = QHBoxLayout()
        hIerrBox1.addWidget(IerrMinLabel)
        hIerrBox1.addWidget(self.IerrMinLineEdit)
        hIerrBox1.addWidget(IerrMaxLabel)
        hIerrBox1.addWidget(self.IerrMaxLineEdit)
        hIerrBox1.addWidget(IerrLimitsSetButton)

        hIerrBox2 = QHBoxLayout()
        hIerrBox2.addWidget(resetIerrButton)

        vIerrBox = QVBoxLayout()
        vIerrBox.addLayout(hIerrBox1)
        vIerrBox.addLayout(hIerrBox2)

        IerrGroupBox = QGroupBox("Set I error limits")
        IerrGroupBox.setLayout(vIerrBox)


        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(PerrGroupBox)
        grid.addWidget(IerrGroupBox)


    def setPerrLimits(self):
        try:
            if float(self.PerrMaxLineEdit.text())<float(self.PerrMinLineEdit.text()):
                MessageWindow(text="Upper limit value is less than lower", type='Error')
            else:
                tivaConn.write('PerrLimits', float(self.PerrMinLineEdit.text()), float(self.PerrMaxLineEdit.text()))
        except ValueError:
            pass
        self.PerrMin, self.PerrMax = tivaConn.read('PerrLimits')
        self.PerrMinLineEdit.setText('{}'.format(self.PerrMin))
        self.PerrMaxLineEdit.setText('{}'.format(self.PerrMax))


    def setIerrLimits(self):
        try:
            if float(self.IerrMaxLineEdit.text())<float(self.IerrMinLineEdit.text()):
                MessageWindow(text="Upper limit value is less than lower", type='Error')
            else:
                tivaConn.write('IerrLimits', float(self.IerrMinLineEdit.text()), float(self.IerrMaxLineEdit.text()))
        except ValueError:
            pass
        self.IerrMin, self.IerrMax = tivaConn.read('IerrLimits')
        self.IerrMinLineEdit.setText('{}'.format(self.IerrMin))
        self.IerrMaxLineEdit.setText('{}'.format(self.IerrMax))


    def resetIerr(self):
        tivaConn.resetIerr()
        MessageWindow(text='Success. Current I-error: {}'.format(tivaConn.read('Ierr')[0]), type='Info')



class AboutWindow(QTabWidget):
    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        self.setWindowTitle("Info & about")
        self.setFixedSize(350, 300)
        self.setWindowIcon(QIcon('img/info.png'))

        self.sysTab = QWidget()
        self.aboutTab = QWidget()
        self.addTab(self.sysTab, "PID-controller")
        self.addTab(self.aboutTab, "About")
        self.initSysTabUI()
        self.initAboutTabUI()

    def initSysTabUI(self):
        layout = QVBoxLayout()
        sysTabText = QLabel("IP-address of MCU: {}\nUDP-port: {}".format(IP, PORT))
        sysTabText.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sysTabText.setWordWrap(True)
        sysTabText.setAlignment(Qt.AlignCenter)
        layout.addWidget(sysTabText)
        self.sysTab.setLayout(layout)
        layout.setAlignment(Qt.AlignCenter)

    def initAboutTabUI(self):
        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.aboutTab.setLayout(layout)
        aboutTabText = QLabel(aboutInfo)
        aboutTabText.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        aboutTabText.setWordWrap(True)
        layout.addWidget(aboutTabText)
        layout.setAlignment(Qt.AlignCenter)




class MainWindow(QMainWindow):

    class FormWidget(QWidget):
        def initUI(self, parent):
            self.Parent = parent

            # QToolTip.setFont(QFont('SansSerif', 10))
            # self.setToolTip('This is a <b>QWidget</b> widget')

            # Group for read/write PID setpoint
            self.setpointReadLabel = QLabel("Current setpoint, V: <b>{0:.3f}</b>".format(tivaConn.read('setpoint')[0]))
            setpointRefreshButton = PicButton(QPixmap("img/refresh.png"), QPixmap("img/refresh_hover.png"), QPixmap("img/refresh_pressed.png"))
            setpointRefreshButton.clicked.connect(self.setpointRefresh)
            setpointRefreshButton.setIcon(QIcon("img/refresh.png"))
            self.setpointWriteLine = QLineEdit()
            self.setpointWriteLine.setPlaceholderText("Enter new setpoint")
            setpointWriteButton = QPushButton('Send...', self)
            setpointWriteButton.clicked.connect(self.setpointWriteButtonClicked)

            setpointHBox1 = QHBoxLayout()
            setpointHBox1.addWidget(self.setpointReadLabel)
            setpointHBox1.addStretch(1)
            setpointHBox1.addWidget(setpointRefreshButton)

            setpointHBox2 = QHBoxLayout()
            setpointHBox2.addWidget(self.setpointWriteLine)
            setpointHBox2.addWidget(setpointWriteButton)

            setpointVBox1 = QVBoxLayout()
            setpointVBox1.addLayout(setpointHBox1)
            setpointVBox1.addLayout(setpointHBox2)

            setpointGroupBox = QGroupBox("Setpoint control")
            setpointGroupBox.setLayout(setpointVBox1)


            # Group for read/write Kp coefficient
            self.KpReadLabel = QLabel("Current Kp value: <b>{0:.3f}</b>".format(tivaConn.read('Kp')[0]))
            KpRefreshButton = PicButton(QPixmap("img/refresh.png"), QPixmap("img/refresh_hover.png"), QPixmap("img/refresh_pressed.png"))
            KpRefreshButton.clicked.connect(self.KpRefresh)
            KpRefreshButton.setIcon(QIcon("img/refresh.png"))
            self.KpWriteLine = QLineEdit()
            self.KpWriteLine.setPlaceholderText("Enter new Kp")
            KpWriteButton = QPushButton('Send...', self)
            KpWriteButton.clicked.connect(self.KpWriteButtonClicked)

            KpHBox1 = QHBoxLayout()
            KpHBox1.addWidget(self.KpReadLabel)
            KpHBox1.addStretch(1)
            KpHBox1.addWidget(KpRefreshButton)

            KpHBox2 = QHBoxLayout()
            KpHBox2.addWidget(self.KpWriteLine)
            KpHBox2.addWidget(KpWriteButton)

            KpVBox1 = QVBoxLayout()
            KpVBox1.addLayout(KpHBox1)
            KpVBox1.addLayout(KpHBox2)

            KpGroupBox = QGroupBox("Kp control")
            KpGroupBox.setLayout(KpVBox1)


            # Group for read/write PID Ki coefficient
            self.KiReadLabel = QLabel("Current Ki value: <b>{0:.3f}</b>".format(tivaConn.read('Ki')[0]))
            KiRefreshButton = PicButton(QPixmap("img/refresh.png"), QPixmap("img/refresh_hover.png"), QPixmap("img/refresh_pressed.png"))
            KiRefreshButton.clicked.connect(self.KiRefresh)
            KiRefreshButton.setIcon(QIcon("img/refresh.png"))
            self.KiWriteLine = QLineEdit()
            self.KiWriteLine.setPlaceholderText("Enter new Ki")
            KiWriteButton = QPushButton('Send...', self)
            KiWriteButton.clicked.connect(self.KiWriteButtonClicked)

            KiHBox1 = QHBoxLayout()
            KiHBox1.addWidget(self.KiReadLabel)
            KiHBox1.addStretch(1)
            KiHBox1.addWidget(KiRefreshButton)

            KiHBox2 = QHBoxLayout()
            KiHBox2.addWidget(self.KiWriteLine)
            KiHBox2.addWidget(KiWriteButton)

            KiVBox = QVBoxLayout()
            KiVBox.addLayout(KiHBox1)
            KiVBox.addLayout(KiHBox2)

            KiGroupBox = QGroupBox("Ki control")
            KiGroupBox.setLayout(KiVBox)


            # Group for read/write PID Kd coefficient
            self.KdReadLabel = QLabel("Current Kd value: <b>{0:.3f}</b>".format(tivaConn.read('Kd')[0]))
            KdRefreshButton = PicButton(QPixmap("img/refresh.png"), QPixmap("img/refresh_hover.png"), QPixmap("img/refresh_pressed.png"))
            KdRefreshButton.clicked.connect(self.KdRefresh)
            KdRefreshButton.setIcon(QIcon("img/refresh.png"))
            self.KdWriteLine = QLineEdit()
            self.KdWriteLine.setPlaceholderText("Enter new Kd")
            KdWriteButton = QPushButton('Send...', self)
            KdWriteButton.clicked.connect(self.KdWriteButtonClicked)

            KdHBox1 = QHBoxLayout()
            KdHBox1.addWidget(self.KdReadLabel)
            KdHBox1.addStretch(1)
            KdHBox1.addWidget(KdRefreshButton)

            KdHBox2 = QHBoxLayout()
            KdHBox2.addWidget(self.KdWriteLine)
            KdHBox2.addWidget(KdWriteButton)

            KdVBox = QVBoxLayout()
            KdVBox.addLayout(KdHBox1)
            KdVBox.addLayout(KdHBox2)

            KdGroupBox = QGroupBox("Kd control")
            KdGroupBox.setLayout(KdVBox)


            self.errorsSettingsWindow = ErrorsSettingsWindow()
            errorsSettingsButton = QPushButton(QIcon('img/set_errors.png'), "Set values of errors...")
            errorsSettingsButton.clicked.connect(self.errorsSettingsWindow.show)


            self.secondsSpinBox = QSpinBox()
            self.secondsSpinBox.setSuffix(" seconds")
            self.secondsSpinBox.setMinimum(0)
            self.secondsSpinBox.setStatusTip('Number of seconds in plot')
            self.secondsSpinBox.setValue(2)


            startPlotButton = QPushButton("Plot")
            startPlotButton.clicked.connect(self.makePlot)


            self.calcAvrgUCheckBox = QCheckBox("Aver. U")
            self.calcAvrgUCheckBox.setStatusTip("Calculate average voltage in next measurement")
            self.avrgULabel = QLabel("U: -")
            self.avrgULabel.setStatusTip('Average voltage of last measurement')

            self.calcAvrgPIDCheckBox = QCheckBox("Aver. PID-output")
            self.calcAvrgPIDCheckBox.setStatusTip("Calculate average PID-output value in next measurement")
            self.avrgPIDLabel = QLabel("PID-output: -")
            self.avrgPIDLabel.setStatusTip('Average PID-output value of last measurement')


            self.uGraph = Graph(xlabel='Time, seconds', ylabel='Voltage, Volts', auto_ylim=False, ymin=0, ymax=3.3)
            self.pidGraph = Graph(ylabel='PID-output')


            self.plotProgressBar = QProgressBar()
            self.Parent.statusBar().addPermanentWidget(self.plotProgressBar)


            self.grid = QGridLayout()
            self.setLayout(self.grid)


            coefficientsBox = QVBoxLayout()
            coefficientsBox.addWidget(setpointGroupBox)
            coefficientsBox.addWidget(KpGroupBox)
            coefficientsBox.addWidget(KiGroupBox)
            coefficientsBox.addWidget(KdGroupBox)
            self.grid.addLayout(coefficientsBox, 0, 0)
            self.grid.addWidget(errorsSettingsButton, 2, 0)
            self.grid.setAlignment(errorsSettingsButton, Qt.AlignCenter)


            makePlotBox = QHBoxLayout()
            makePlotBox.addWidget(self.secondsSpinBox)
            makePlotBox.setAlignment(self.secondsSpinBox, Qt.AlignRight)
            makePlotBox.addWidget(startPlotButton)
            makePlotBox.setAlignment(startPlotButton, Qt.AlignLeft)
            self.grid.addLayout(makePlotBox, 4, 0)


            avrgUBox = QHBoxLayout()
            avrgUBox.addWidget(self.calcAvrgUCheckBox)
            avrgUBox.addWidget(self.avrgULabel)
            self.grid.addLayout(avrgUBox, 5, 0)

            avrgPIDBox = QHBoxLayout()
            avrgPIDBox.addWidget(self.calcAvrgPIDCheckBox)
            avrgPIDBox.addWidget(self.avrgPIDLabel)
            self.grid.addLayout(avrgPIDBox, 6, 0)


            self.uGraphToolbar = self.uGraph.getGraphToolbar()
            self.pidGraphToolbar = self.pidGraph.getGraphToolbar()

            self.plotBox = QVBoxLayout()
            self.plotBox.addWidget(self.uGraph)
            self.plotBox.addWidget(self.uGraphToolbar)
            self.plotBox.setAlignment(self.uGraphToolbar, Qt.AlignCenter)
            self.plotBox.addWidget(self.pidGraph)
            self.plotBox.addWidget(self.pidGraphToolbar)
            self.plotBox.setAlignment(self.pidGraphToolbar, Qt.AlignCenter)

            self.grid.addLayout(self.plotBox, 0, 1, 7, 1)

            self.setLayout(self.grid)


        def setpointRefresh(self):
            self.setpointReadLabel.setText("Current setpoint, V: <b>{0:.3f}</b>".format(tivaConn.read('setpoint')[0]))

        def KpRefresh(self):
            self.KpReadLabel.setText("Current Kp value: <b>{0:.3f}</b>".format(tivaConn.read('Kp')[0]))

        def KiRefresh(self):
            self.KiReadLabel.setText("Current Ki value: <b>{0:.3f}</b>".format(tivaConn.read('Ki')[0]))

        def KdRefresh(self):
            self.KdReadLabel.setText("Current Kd value: <b>{0:.3f}</b>".format(tivaConn.read('Kd')[0]))


        def setpointWriteButtonClicked(self):
            try:
                if float(self.setpointWriteLine.text()) <= 3.3 and float(self.setpointWriteLine.text()) >= 0:
                    tivaConn.write('setpoint', float(self.setpointWriteLine.text()))
                else:
                    MessageWindow(text="Setpoint value must be in interval [0; 3.3] Volts!", type="Warning")
            except ValueError:
                pass
            self.setpointWriteLine.clear()
            self.setpointRefresh()


        def KpWriteButtonClicked(self):
            try:
                tivaConn.write('Kp', float(self.KpWriteLine.text()))
            except ValueError:
                pass
            self.KpWriteLine.clear()
            self.KpRefresh()


        def KiWriteButtonClicked(self):
            try:
                tivaConn.write('Ki', float(self.KiWriteLine.text()))
            except ValueError:
                pass
            self.KiWriteLine.clear()
            self.KiRefresh()


        def KdWriteButtonClicked(self):
            try:
                tivaConn.write('Kd', float(self.KdWriteLine.text()))
            except ValueError:
                pass
            self.KdWriteLine.clear()
            self.KdRefresh()


        def makePlot(self):
            timeArray = []
            uArray = []
            pidArray = []

            if self.Parent.settingsWindow.onlyUGraphRadioButton.isChecked():
                startTime = time_time()
                while time_time()-startTime < self.secondsSpinBox.value():
                    timeArray.append(time_time()-startTime)
                    uArray.append(tivaConn.read('U')[0])
                    pidArray.append(0.0)
                    self.plotProgressBar.setValue(100.0*((time_time()-startTime)/self.secondsSpinBox.value()))
                    QApplication.processEvents()

            elif self.Parent.settingsWindow.onlyPIDGraphRadioButton.isChecked():
                startTime = time_time()
                while time_time()-startTime < self.secondsSpinBox.value():
                    timeArray.append(time_time()-startTime)
                    pidArray.append(tivaConn.read('PID')[0])
                    uArray.append(0.0)
                    self.plotProgressBar.setValue(100.0*((time_time()-startTime)/self.secondsSpinBox.value()))
                    QApplication.processEvents()

            elif self.Parent.settingsWindow.bothGraphsRadioButton.isChecked():
                startTime = time_time()
                while time_time()-startTime < self.secondsSpinBox.value():
                    timeArray.append(time_time()-startTime)
                    uArray.append(tivaConn.read('U')[0])
                    pidArray.append(tivaConn.read('PID')[0])
                    self.plotProgressBar.setValue(100.0*((time_time()-startTime)/self.secondsSpinBox.value()))
                    QApplication.processEvents()

            self.Parent.statusBar().showMessage("Points in plot: {}".format(len(timeArray)))

            self.uGraph.setParent(None)
            self.uGraphToolbar.setParent(None)
            if self.Parent.settingsWindow.onlyPIDGraphRadioButton.isChecked():
                self.uGraph = Graph(xlabel='Time, seconds', ylabel='Voltage, Volts', auto_ylim=False, ymin=0, ymax=3.3)
            else:
                self.uGraph = Graph(Xarray=timeArray, Yarray=uArray, xlabel='Time, seconds', ylabel='Voltage, Volts', auto_ylim=False, ymin=0, ymax=3.3)
            self.uGraphToolbar = self.uGraph.getGraphToolbar()

            self.pidGraph.setParent(None)
            self.pidGraphToolbar.setParent(None)
            if self.Parent.settingsWindow.onlyUGraphRadioButton.isChecked():
                self.pidGraph = Graph(ylabel='PID-output')
            else:
                self.pidGraph = Graph(Xarray=timeArray, Yarray=pidArray, ylabel='PID-output')
            self.pidGraphToolbar = self.pidGraph.getGraphToolbar()

            self.plotBox.addWidget(self.uGraph)
            self.plotBox.addWidget(self.uGraphToolbar)
            self.plotBox.setAlignment(self.uGraphToolbar, Qt.AlignCenter)

            self.plotBox.addWidget(self.pidGraph)
            self.plotBox.addWidget(self.pidGraphToolbar)
            self.plotBox.setAlignment(self.pidGraphToolbar, Qt.AlignCenter)

            if self.calcAvrgUCheckBox.isChecked():
                if not self.Parent.settingsWindow.onlyPIDGraphRadioButton.isChecked():
                    self.avrgULabel.setText("U: {0:.3f}".format(numpy_mean(uArray)))
                else:
                    self.avrgULabel.setText("U: -")
            else:
                self.avrgULabel.setText("U: -")

            if self.calcAvrgPIDCheckBox.isChecked():
                if not self.Parent.settingsWindow.onlyUGraphRadioButton.isChecked():
                    self.avrgPIDLabel.setText("PID-output: {0:.3f}".format(numpy_mean(pidArray)))
                else:
                    self.avrgPIDLabel.setText("PID-output: -")
            else:
                self.avrgPIDLabel.setText("PID-output: -")



    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("PID GUI application")
        self.setWindowIcon(QIcon('img/icon.png'))

        self.formWidget = self.FormWidget()
        self.formWidget.initUI(self)
        self.setCentralWidget(self.formWidget)

        exitAction = QAction(QIcon('img/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(app.quit)

        infoAction = QAction(QIcon('img/info.png'), 'Info', self)
        infoAction.setShortcut('Ctrl+I')
        infoAction.setStatusTip('Info & about')
        self.aboutWindow = AboutWindow()
        infoAction.triggered.connect(self.aboutWindow.show)

        settingsAction = QAction(QIcon('img/settings.png'), 'Settings', self)
        settingsAction.setShortcut('Ctrl+P')
        settingsAction.setStatusTip('Settings')
        self.settingsWindow = SettingsWindow()
        settingsAction.triggered.connect(self.settingsWindow.show)

        toolbar = self.addToolBar('')
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.addAction(exitAction)
        toolbar.addAction(infoAction)
        toolbar.addAction(settingsAction)

        # menubar = self.menuBar()
        mainMenu = self.menuBar().addMenu('&Menu')
        mainMenu.addAction(exitAction)
        mainMenu.addAction(infoAction)
        mainMenu.addAction(settingsAction)

        if DEMO_MODE:
            self.statusBar().addWidget(QLabel("<font color='red'>Demo mode</font>"))




def checkConnectionTimerHandler():
    if tivaConn.checkConnection():
        connLostHandler()
    else:
        if tivaConn.OFFLINE_MODE:
            tivaConn.OFFLINE_MODE = False
            refreshAllPIDvalues()
            mainWindow.statusBar().removeWidget(connLostStatusBarLabel)
            mainWindow.statusBar().showMessage('Reconnected')


# handler function for connLost slot
def connLostHandler():
    if not tivaConn.OFFLINE_MODE:
        tivaConn.OFFLINE_MODE = True
        mainWindow.statusBar().addWidget(connLostStatusBarLabel)
        MessageWindow(text='Connection was lost. App going to Offline mode and will be trying to reconnect', type='Warning')


def refreshAllPIDvalues():
    mainWindow.formWidget.setpointRefresh()
    mainWindow.formWidget.KpRefresh()
    mainWindow.formWidget.KiRefresh()
    mainWindow.formWidget.KdRefresh()
    mainWindow.formWidget.errorsSettingsWindow.PerrMin, mainWindow.formWidget.errorsSettingsWindow.PerrMax = tivaConn.read('PerrLimits')
    mainWindow.formWidget.errorsSettingsWindow.PerrMinLineEdit.setText('{}'.format(mainWindow.formWidget.errorsSettingsWindow.PerrMin))
    mainWindow.formWidget.errorsSettingsWindow.PerrMaxLineEdit.setText('{}'.format(mainWindow.formWidget.errorsSettingsWindow.PerrMax))
    mainWindow.formWidget.errorsSettingsWindow.IerrMin, mainWindow.formWidget.errorsSettingsWindow.IerrMax = tivaConn.read('IerrLimits')
    mainWindow.formWidget.errorsSettingsWindow.IerrMinLineEdit.setText('{}'.format(mainWindow.formWidget.errorsSettingsWindow.IerrMin))
    mainWindow.formWidget.errorsSettingsWindow.IerrMaxLineEdit.setText('{}'.format(mainWindow.formWidget.errorsSettingsWindow.IerrMax))




if __name__ == '__main__':
    aboutInfo = "v.'{}'\n(C) Andrey Chufyrev, 2017\n\nPython v.{} on {}.\n\nThis is the Python-based GUI application for PID-controller on the base of "\
                "Texas Instruments TIVA-C MCU with remote control (UDP/IP/Ethernet) via Microchip ENC28J60.\n\nPackages versions:\n\tmatplotlib: {}\n\tnumpy: {}\n"\
                "\tPyQt: {}\n\tQt: {}".format(__version__, sys.version[0:5], sys.platform, matplotlib___version__, numpy___version__, PYQT_VERSION_STR, QT_VERSION_STR)
    print(aboutInfo)

    ORGANIZATION_NAME = 'Andrey Chufyrev'
    APPLICATION_NAME = 'PID GUI'
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)


    settings = QSettings()
    IP = settings.value("network/ip")
    PORT = settings.value("network/port", type=int)
    if type(IP) == type(settings.value("non_existent_settings_key")):
        IP = '192.168.1.110'
        PORT = 1200

    print("\nDefault IP/PORT pair is: {}/{}. If it's correct press ENTER. If you want to change these settings, please input new values as was given above. "\
          "This pair will be the new default.".format(IP, PORT))
    while (True):
        try:
            input_str = input("Input here: ")
            if input_str != '':
                IP = input_str[:input_str.index('/')]
                PORT = int(input_str[input_str.index('/')+1:])

                print("You entered:\n\tIP:   {}\n\tPORT: {}\nIf it's correct press ENTER, else input any symbol.".format(IP, PORT))
                input_str = input("ENTER? ")
                if input_str != '':
                    continue
                settings.setValue("network/ip", IP)
                settings.setValue("network/port", PORT)
                settings.sync()
                break
            else:
                break
        except ValueError:
            print("Wrong input! Must be like: 192.168.1.110/1200. Try again.")


    app = QApplication(sys.argv)

    tivaConn = MCUconn(IP, PORT)
    # widget for showing in statusbar when connection lost
    connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")
    DEMO_MODE = False
    if tivaConn.checkConnection():
        tivaConn.OFFLINE_MODE = True
        DEMO_MODE = True
        print("\nDemo mode entered")
        MessageWindow(text="Due to no connection to regulator the application will start in Demo mode. All values are random. "\
                           "To exit Demo mode please restart application.")
    else:
        # if connection is present and no demo mode then create timer for connection checking
        checkConnectionTimer = QTimer()
        checkConnectionTimer.timeout.connect(checkConnectionTimerHandler)
        checkConnectionTimer.start(5000)  # every 5 seconds
        # also create handler function for connection lost (for example, when reading some coefficient from MCU)
        tivaConn.connLost.signal.connect(connLostHandler)
    # save values for restoring
    tivaConn.saveCurrentValues()

    mainWindow = MainWindow()
    mainWindow.show()

    print('\nloaded.\n')
    sys.exit(app.exec_())
