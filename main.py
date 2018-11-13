import functools
import string

if __name__ == '__main__':
    print('loading...\n')
    __version__ = 'zeta'

import sys
from numpy import mean as numpy_mean, __version__ as numpy___version__
from time import time as time_time
# from matplotlib import __version__ as matplotlib___version__
matplotlib___version__ = 0.0

from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,\
                            QApplication, QSpinBox, QStatusBar, QProgressBar, QLineEdit, QCheckBox, QGridLayout,\
                            QTabWidget, QMainWindow, QToolTip, QAction, QLayout, QSizePolicy, QButtonGroup
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QCoreApplication, QSettings, Qt, QT_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR
import qdarkstyle

from miscgraphics import PicButton, MessageWindow, CustomGraphicsLayoutWidget
from mcuconn import MCUconn

import numpy as np



class SettingsWindow(QWidget):

    def __init__(self, parent=None):

        super(SettingsWindow, self).__init__(parent)

        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon('img/settings.png'))

        # self.onlyUGraphRadioButton = QRadioButton("Plot only U(t) graph")
        # self.onlyPIDGraphRadioButton = QRadioButton("Plot only PID-output(t) graph")
        # self.bothGraphsRadioButton = QRadioButton("Plot both graphs concurrently")
        # self.bothGraphsRadioButton.setChecked(True)

        # chooseNumberOfGraphsVBox = QVBoxLayout()
        # chooseNumberOfGraphsVBox.addWidget(self.onlyUGraphRadioButton)
        # chooseNumberOfGraphsVBox.addWidget(self.onlyPIDGraphRadioButton)
        # chooseNumberOfGraphsVBox.addWidget(self.bothGraphsRadioButton)
        # chooseNumberOfGraphsGroupBox = QGroupBox("Graphs to plot:")
        # chooseNumberOfGraphsGroupBox.setLayout(chooseNumberOfGraphsVBox)


        networkGroupBox = QGroupBox("Controller connection")
        networkHBox = QHBoxLayout()
        networkGroupBox.setLayout(networkHBox)

        self.ipLineEdit = QLineEdit(contIP)
        self.portLineEdit = QLineEdit(str(contPort))
        networkHBox.addWidget(self.ipLineEdit)
        networkHBox.addWidget(self.portLineEdit)



        themeHBox = QHBoxLayout()
        themeGroupBox = QGroupBox('Theme')
        themeGroupBox.setLayout(themeHBox)

        self.themeLightRadioButton = QRadioButton('Light')
        self.themeDarkRadioButton = QRadioButton('Dark')
        themeButtonGroup = QButtonGroup(themeGroupBox)
        themeButtonGroup.addButton(self.themeLightRadioButton)
        themeButtonGroup.addButton(self.themeDarkRadioButton)

        if theme == 'light':
            self.themeLightRadioButton.setChecked(True)
        else:
            self.themeDarkRadioButton.setChecked(True)
        self.themeLightRadioButton.toggled.connect(self.themeSet)

        themeHBox.addWidget(self.themeLightRadioButton)
        themeHBox.addWidget(self.themeDarkRadioButton)



        # TODO: graphs settings



        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(themeGroupBox)
        grid.addWidget(networkGroupBox)
        # grid.addWidget(restoreLabel)
        # grid.addWidget(restoreButton)
        # grid.addWidget(saveToEEPROMLabel)
        # grid.addWidget(saveToEEPROMButton)


    def themeSet(self):
        if self.themeLightRadioButton.isChecked():
            theme = 'light'
        else:
            theme = 'dark'
        settings.setValue("appearance/theme", theme)
        MessageWindow(text="Theme is saved. Please restart the application to take effect.", type='Info')



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
                MessageWindow(text="Upper limit value is less than lower!", type='Error')
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
                MessageWindow(text="Upper limit value is less than lower!", type='Error')
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
        sysTabText = QLabel("IP-address of MCU: {}\nUDP-port: {}".format(contIP, contPort))
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




class ValueGroupBox(QGroupBox):
    """

    """

    def __init__(self, label, conn, parent=None):

        super(ValueGroupBox, self).__init__(parent)

        self.setTitle(f"{label.capitalize()} control")

        self.label = label
        self.conn = conn

        self.valLabelTemplate = string.Template("Current $label: <b>{:.3f}</b>").safe_substitute(label=label)
        self.valLabel = QLabel()
        self.refreshVal()
        refreshButton = PicButton(QPixmap("img/refresh.png"), QPixmap("img/refresh_hover.png"),
                                  QPixmap("img/refresh_pressed.png"))
        refreshButton.clicked.connect(self.refreshVal)
        refreshButton.setIcon(QIcon("img/refresh.png"))
        self.writeLine = QLineEdit()
        self.writeLine.setPlaceholderText(f"Enter new '{label}'")
        writeButton = QPushButton('Send', self)
        writeButton.clicked.connect(self.writeButtonClicked)

        hBox1 = QHBoxLayout()
        hBox1.addWidget(self.valLabel)
        hBox1.addStretch(1)
        hBox1.addWidget(refreshButton)

        hBox2 = QHBoxLayout()
        hBox2.addWidget(self.writeLine)
        hBox2.addWidget(writeButton)

        vBox1 = QVBoxLayout()
        vBox1.addLayout(hBox1)
        vBox1.addLayout(hBox2)

        self.setLayout(vBox1)


    def refreshVal(self):
        self.valLabel.setText(self.valLabelTemplate.format(self.conn.read(self.label)[0]))


    def writeButtonClicked(self):
        try:
            self.conn.write(self.label, float(self.writeLine.text()))
        except ValueError:
            pass
        self.writeLine.clear()
        self.refreshVal()



class CentralWidget(QWidget):

    def __init__(self, parent=None):

        super(CentralWidget, self).__init__(parent)

        # Group for read/write PID setpoint
        setpointGroupBox = ValueGroupBox('setpoint', tivaConn)
        # Group for read/write Kp coefficient
        KpGroupBox = ValueGroupBox('Kp', tivaConn)
        # Group for read/write PID Ki coefficient
        KiGroupBox = ValueGroupBox('Ki', tivaConn)
        # Group for read/write PID Kd coefficient
        KdGroupBox = ValueGroupBox('Kd', tivaConn)

        self.errorsSettingsWindow = ErrorsSettingsWindow()
        # errorsSettingsButton = QPushButton(QIcon('img/set_errors.png'), "Set values of errors...")
        # errorsSettingsButton.clicked.connect(self.errorsSettingsWindow.show)

        self.graphs = CustomGraphicsLayoutWidget(nPoints=200, procVarRange=(0.0, 10.0), contOutRange=(0.0, 10.0),
                                                 interval=17, theme=theme, start=True)

        # self.calcAvrgUCheckBox = QCheckBox("Aver. U")
        # self.calcAvrgUCheckBox.setStatusTip("Calculate average voltage in next measurement")
        self.avrgULabel = self.graphs.procVarAverLabel
        self.avrgULabel.setStatusTip('Average voltage of last measurement')

        # self.calcAvrgPIDCheckBox = QCheckBox("Aver. PID-output")
        # self.calcAvrgPIDCheckBox.setStatusTip("Calculate average PID-output value in next measurement")
        self.avrgPIDLabel = self.graphs.contOutAverLabel
        self.avrgPIDLabel.setStatusTip('Average PID-output value of last measurement')

        grid = QGridLayout()
        self.setLayout(grid)

        grid.addWidget(setpointGroupBox, 0, 0, 3, 2)
        grid.addWidget(KpGroupBox, 3, 0, 3, 2)
        grid.addWidget(KiGroupBox, 6, 0, 3, 2)
        grid.addWidget(KdGroupBox, 9, 0, 3, 2)

        grid.addWidget(self.graphs, 0, 2, 14, 4)

        # grid.addWidget(errorsSettingsButton, 12, 0, 1, 2)
        # grid.setAlignment(errorsSettingsButton, Qt.AlignCenter)
        #
        # # restoreLabel = QLabel("Restore all MCU values to values at program start time")
        # restoreButton = QPushButton("Restore")
        # restoreButton.setStatusTip("Restore all controller parameters to values at the program start time")
        # restoreButton.clicked.connect(self.restore)
        #
        # # saveToEEPROMLabel = QLabel("Save current controller configuration to EEPROM")
        # saveToEEPROMButton = QPushButton("Save to EEPROM")
        # saveToEEPROMButton.setStatusTip("Save current controller configuration to EEPROM")
        # saveToEEPROMButton.clicked.connect(self.saveToEEPROM)
        #
        # grid.addWidget(restoreButton, 13, 0, 1, 2)
        # grid.setAlignment(restoreButton, Qt.AlignCenter)
        # grid.addWidget(saveToEEPROMButton, 14, 0, 1, 2)
        # grid.setAlignment(saveToEEPROMButton, Qt.AlignCenter)


        avrgUBox = QHBoxLayout()
        avrgUBox.addWidget(QLabel("Process Variable:"))
        avrgUBox.addWidget(self.avrgULabel)
        grid.addLayout(avrgUBox, 12, 0, 1, 2)

        avrgPIDBox = QHBoxLayout()
        avrgPIDBox.addWidget(QLabel("Controller Output:"))
        avrgPIDBox.addWidget(self.avrgPIDLabel)
        grid.addLayout(avrgPIDBox, 13, 0, 1, 2)


        # self.plotBox = QVBoxLayout()
        # self.plotBox.addWidget(self.uGraph)
        # self.plotBox.addWidget(self.uGraphToolbar)
        # self.plotBox.setAlignment(self.uGraphToolbar, Qt.AlignCenter)
        # self.plotBox.addWidget(self.pidGraph)
        # self.plotBox.addWidget(self.pidGraphToolbar)
        # self.plotBox.setAlignment(self.pidGraphToolbar, Qt.AlignCenter)
        #
        # self.grid.addLayout(self.plotBox, 0, 1, 7, 1)


def restore(conn):
    conn.restoreValues()
    refreshAllPIDvalues()

def saveToEEPROM(conn):
    if conn.saveToEEPROM() == 0:
        MessageWindow(text='Successfully saved', type='Info')
        refreshAllPIDvalues()
    else:
        MessageWindow(text='Saving failed!', type='Error')




class MainWindow(QMainWindow):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)

        self.setWindowTitle("PID controller GUI")
        self.setWindowIcon(QIcon('img/icon.png'))

        self.centralWidget = CentralWidget()
        self.setCentralWidget(self.centralWidget)


        exitAction = QAction(QIcon('img/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('[Ctrl+Q] Exit application')
        exitAction.triggered.connect(app.quit)

        infoAction = QAction(QIcon('img/info.png'), 'Info', self)
        infoAction.setShortcut('Ctrl+I')
        infoAction.setStatusTip('[Ctrl+I] Info & about')
        self.aboutWindow = AboutWindow()
        infoAction.triggered.connect(self.aboutWindow.show)

        settingsAction = QAction(QIcon('img/settings.png'), 'Settings', self)
        settingsAction.setShortcut('Ctrl+P')
        settingsAction.setStatusTip('[Ctrl+P] Settings')
        self.settingsWindow = SettingsWindow()
        settingsAction.triggered.connect(self.settingsWindow.show)

        mainToolbar = self.addToolBar('main')
        mainToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        mainToolbar.addAction(exitAction)
        mainToolbar.addAction(infoAction)
        mainToolbar.addAction(settingsAction)


        errorsLimitsAction = QAction(QIcon(), 'Errors limits', self)
        errorsLimitsAction.setShortcut('E')
        errorsLimitsAction.setStatusTip("[E] Set values of errors limits")
        errorsLimitsAction.triggered.connect(self.centralWidget.errorsSettingsWindow.show)

        restoreValuesAction = QAction(QIcon(), 'Restore controller', self)
        restoreValuesAction.setShortcut('R')
        restoreValuesAction.setStatusTip('[R] Restore all controller parameters to values at the program start time')
        restoreValuesAction.triggered.connect(functools.partial(restore, tivaConn))

        saveToEEPROMAction = QAction(QIcon(), 'Save to EEPROM', self)
        saveToEEPROMAction.setShortcut('S')
        saveToEEPROMAction.setStatusTip("[S] Save current controller configuration to EEPROM")
        # saveToEEPROMAction.triggered.connect(self.centralWidget.saveToEEPROM)
        saveToEEPROMAction.triggered.connect(functools.partial(saveToEEPROM, tivaConn))

        contToolbar = self.addToolBar('controller')
        contToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        contToolbar.addAction(errorsLimitsAction)
        contToolbar.addAction(restoreValuesAction)
        contToolbar.addAction(saveToEEPROMAction)


        playpauseAction = QAction(QIcon('img/play_pause.png'), 'Play/Pause', self)
        playpauseAction.setShortcut('P')
        playpauseAction.setStatusTip('[P] Play/pause graphs')
        # playpauseAction.triggered.connect(self.formWidget.graphs.toggle_live_graphs)
        playpauseAction.triggered.connect(self.playpauseGraphs)

        graphsToolbar = self.addToolBar('graphs')
        graphsToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        graphsToolbar.addAction(playpauseAction)
        self.playpauseButton = graphsToolbar.widgetForAction(playpauseAction)
        self.playpauseButton.setCheckable(True)

        # menubar = self.menuBar()
        mainMenu = self.menuBar().addMenu('&Menu')
        mainMenu.addAction(exitAction)
        mainMenu.addAction(infoAction)
        mainMenu.addAction(settingsAction)

        if DEMO_MODE:
            self.statusBar().addWidget(QLabel("<font color='red'>Demo mode</font>"))

    def playpauseGraphs(self):
        if self.centralWidget.graphs.run:
            self.playpauseButton.setChecked(True)
        else:
            self.playpauseButton.setChecked(False)
        self.centralWidget.graphs.toggle_live_graphs()



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
    mainWindow.centralWidget.setpointGroupBox.refreshVal()
    mainWindow.centralWidget.KpGroupBox.refreshVal()
    mainWindow.centralWidget.KiGroupBox.refreshVal()
    mainWindow.centralWidget.KdGroupBox.refreshVal()
    mainWindow.centralWidget.errorsSettingsWindow.PerrMin, mainWindow.centralWidget.errorsSettingsWindow.PerrMax = tivaConn.read('PerrLimits')
    mainWindow.centralWidget.errorsSettingsWindow.PerrMinLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.PerrMin))
    mainWindow.centralWidget.errorsSettingsWindow.PerrMaxLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.PerrMax))
    mainWindow.centralWidget.errorsSettingsWindow.IerrMin, mainWindow.centralWidget.errorsSettingsWindow.IerrMax = tivaConn.read('IerrLimits')
    mainWindow.centralWidget.errorsSettingsWindow.IerrMinLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.IerrMin))
    mainWindow.centralWidget.errorsSettingsWindow.IerrMaxLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.IerrMax))




if __name__ == '__main__':

    aboutInfo = "la"

    ORGANIZATION_NAME = 'Andrey Chufyrev'
    APPLICATION_NAME = 'PID GUI'
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)


    settings = QSettings()

    contIP = settings.value("network/ip", type=str, defaultValue='192.168.1.110')
    contPort = settings.value("network/port", type=int, defaultValue=1200)
    theme = settings.value("appearance/theme", type=str, defaultValue='light')
    if not settings.contains("network/ip"):
        settings.setValue("network/ip", contIP)
        settings.setValue("network/port", contPort)
        settings.setValue("appearance/theme", theme)

    app = QApplication(sys.argv)
    if theme == 'dark':
        # TODO: maybe import qdarkstyle only there (need to see pyinstaller capabilities)
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    tivaConn = MCUconn(contIP, contPort)
    # widget for showing in statusbar when connection lost
    connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")
    DEMO_MODE = False
    if tivaConn.checkConnection():
        tivaConn.OFFLINE_MODE = True
        DEMO_MODE = True
        print("\nDemo mode entered")
        # MessageWindow(text="Due to no connection to regulator the application will start in Demo mode. All values are random. "\
        #                    "To exit Demo mode please restart the application.")
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

    sys.exit(app.exec_())
