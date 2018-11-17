import functools

import sys

from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,\
                            QApplication, QSpinBox, QStatusBar, QProgressBar, QLineEdit, QCheckBox, QGridLayout,\
                            QTabWidget, QMainWindow, QToolTip, QAction, QLayout, QSizePolicy, QButtonGroup
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QCoreApplication, QSettings, Qt, QT_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR
import qdarkstyle

from miscgraphics import PicButton, MessageWindow, ValueGroupBox, CustomGraphicsLayoutWidget
from mcuconn import MCUconn
from settings import Settings, SettingsWindow
from errorssettings import ErrorsSettingsWindow
from about import AboutWindow

import numpy as np



class CentralWidget(QWidget):

    def __init__(self, app, parent=None):

        super(CentralWidget, self).__init__(parent)

        self.app = app

        # Group for read/write PID setpoint
        self.setpointGroupBox = ValueGroupBox('setpoint', app.conn)
        # Group for read/write Kp coefficient
        self.KpGroupBox = ValueGroupBox('Kp', app.conn)
        # Group for read/write PID Ki coefficient
        self.KiGroupBox = ValueGroupBox('Ki', app.conn)
        # Group for read/write PID Kd coefficient
        self.KdGroupBox = ValueGroupBox('Kd', app.conn)

        self.errorsSettingsWindow = ErrorsSettingsWindow(app)
        # errorsSettingsButton = QPushButton(QIcon('img/set_errors.png'), "Set values of errors...")
        # errorsSettingsButton.clicked.connect(self.errorsSettingsWindow.show)

        self.graphs = CustomGraphicsLayoutWidget(nPoints=app.settings['graphs']['numberOfPoints'], procVarRange=(0.0, 10.0), contOutRange=(0.0, 10.0),
                                                 interval=app.settings['graphs']['updateInterval'], theme=app.settings['appearance']['theme'], start=True)

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

        grid.addWidget(self.setpointGroupBox, 0, 0, 3, 2)
        grid.addWidget(self.KpGroupBox, 3, 0, 3, 2)
        grid.addWidget(self.KiGroupBox, 6, 0, 3, 2)
        grid.addWidget(self.KdGroupBox, 9, 0, 3, 2)

        grid.addWidget(self.graphs, 0, 2, 14, 4)


        avrgUBox = QHBoxLayout()
        avrgUBox.addWidget(QLabel("Process Variable:"))
        avrgUBox.addWidget(self.avrgULabel)
        grid.addLayout(avrgUBox, 12, 0, 1, 2)

        avrgPIDBox = QHBoxLayout()
        avrgPIDBox.addWidget(QLabel("Controller Output:"))
        avrgPIDBox.addWidget(self.avrgPIDLabel)
        grid.addLayout(avrgPIDBox, 13, 0, 1, 2)



    def refreshAllPIDvalues(self):
        self.setpointGroupBox.refreshVal()
        self.KpGroupBox.refreshVal()
        self.KiGroupBox.refreshVal()
        self.KdGroupBox.refreshVal()
        self.errorsSettingsWindow.PerrMin, self.errorsSettingsWindow.PerrMax = self.app.conn.read('PerrLimits')
        self.errorsSettingsWindow.PerrMinLineEdit.setText('{}'.format(self.errorsSettingsWindow.PerrMin))
        self.errorsSettingsWindow.PerrMaxLineEdit.setText('{}'.format(self.errorsSettingsWindow.PerrMax))
        self.errorsSettingsWindow.IerrMin, self.errorsSettingsWindow.IerrMax = self.app.conn.read('IerrLimits')
        self.errorsSettingsWindow.IerrMinLineEdit.setText('{}'.format(self.errorsSettingsWindow.IerrMin))
        self.errorsSettingsWindow.IerrMaxLineEdit.setText('{}'.format(self.errorsSettingsWindow.IerrMax))


def restore(conn):
    conn.restoreValues()
    app.mainWindow.centralWidget.refreshAllPIDvalues()

def saveToEEPROM(conn):
    if conn.saveToEEPROM() == 0:
        MessageWindow(text='Successfully saved', type='Info')
        app.mainWindow.centralWidget.refreshAllPIDvalues()
    else:
        MessageWindow(text='Saving failed!', type='Error')




class MainWindow(QMainWindow):

    def __init__(self, app, parent=None):

        super(MainWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle("PID controller GUI")
        self.setWindowIcon(QIcon('img/icon.png'))

        self.centralWidget = CentralWidget(app)
        self.setCentralWidget(self.centralWidget)


        exitAction = QAction(QIcon('img/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('[Ctrl+Q] Exit application')
        exitAction.triggered.connect(self.app.quit)

        infoAction = QAction(QIcon('img/info.png'), 'Info', self)
        infoAction.setShortcut('Ctrl+I')
        infoAction.setStatusTip('[Ctrl+I] Application Info & About')
        self.aboutWindow = AboutWindow(app)
        infoAction.triggered.connect(self.aboutWindow.show)

        settingsAction = QAction(QIcon('img/settings.png'), 'Settings', self)
        settingsAction.setShortcut('Ctrl+P')
        settingsAction.setStatusTip('[Ctrl+P] Application Settings')
        self.settingsWindow = SettingsWindow(app)
        settingsAction.triggered.connect(self.settingsWindow.show)

        appToolbar = self.addToolBar('app')
        appToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        appToolbar.addAction(exitAction)
        appToolbar.addAction(infoAction)
        appToolbar.addAction(settingsAction)


        errorsLimitsAction = QAction(QIcon("img/set_errors.png"), 'Errors limits', self)
        errorsLimitsAction.setShortcut('E')
        errorsLimitsAction.setStatusTip("[E] Set values of errors limits")
        errorsLimitsAction.triggered.connect(self.centralWidget.errorsSettingsWindow.show)

        restoreValuesAction = QAction(QIcon("img/restore.png"), 'Restore controller', self)
        restoreValuesAction.setShortcut('R')
        restoreValuesAction.setStatusTip('[R] Restore all controller parameters to values at the program start time')
        restoreValuesAction.triggered.connect(functools.partial(restore, self.app.conn))

        saveToEEPROMAction = QAction(QIcon("img/eeprom.png"), 'Save to EEPROM', self)
        saveToEEPROMAction.setShortcut('S')
        saveToEEPROMAction.setStatusTip("[S] Save current controller configuration to EEPROM")
        # saveToEEPROMAction.triggered.connect(self.centralWidget.saveToEEPROM)
        saveToEEPROMAction.triggered.connect(functools.partial(saveToEEPROM, self.app.conn))

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

        if self.app.DEMO_MODE:
            self.statusBar().addWidget(QLabel("<font color='red'>Demo mode</font>"))

    def playpauseGraphs(self):
        if self.centralWidget.graphs.run:
            self.playpauseButton.setChecked(True)
        else:
            self.playpauseButton.setChecked(False)
        self.centralWidget.graphs.toggle_live_graphs()



# def connCheckTimerHandler():
#     if tivaConn.checkConnection():
#         connLostHandler()
#     else:
#         if tivaConn.OFFLINE_MODE:
#             tivaConn.OFFLINE_MODE = False
#             refreshAllPIDvalues()
#             mainWindow.statusBar().removeWidget(connLostStatusBarLabel)
#             mainWindow.statusBar().showMessage('Reconnected')
#
#
# # handler function for connLost slot
# def connLostHandler():
#     if not tivaConn.OFFLINE_MODE:
#         tivaConn.OFFLINE_MODE = True
#         mainWindow.statusBar().addWidget(connLostStatusBarLabel)
#         MessageWindow(text='Connection was lost. App going to Offline mode and will be trying to reconnect', type='Warning')
#
#
# def refreshAllPIDvalues():
#     mainWindow.centralWidget.setpointGroupBox.refreshVal()
#     mainWindow.centralWidget.KpGroupBox.refreshVal()
#     mainWindow.centralWidget.KiGroupBox.refreshVal()
#     mainWindow.centralWidget.KdGroupBox.refreshVal()
#     mainWindow.centralWidget.errorsSettingsWindow.PerrMin, mainWindow.centralWidget.errorsSettingsWindow.PerrMax = tivaConn.read('PerrLimits')
#     mainWindow.centralWidget.errorsSettingsWindow.PerrMinLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.PerrMin))
#     mainWindow.centralWidget.errorsSettingsWindow.PerrMaxLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.PerrMax))
#     mainWindow.centralWidget.errorsSettingsWindow.IerrMin, mainWindow.centralWidget.errorsSettingsWindow.IerrMax = tivaConn.read('IerrLimits')
#     mainWindow.centralWidget.errorsSettingsWindow.IerrMinLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.IerrMin))
#     mainWindow.centralWidget.errorsSettingsWindow.IerrMaxLineEdit.setText('{}'.format(mainWindow.centralWidget.errorsSettingsWindow.IerrMax))



class MainApplication(QApplication):

    def __init__(self, argv):

        super(MainApplication, self).__init__(argv)

        self.settings = Settings(defaults='defaultSettings.json')

        if self.settings['appearance']['theme'] == 'dark':
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.conn = MCUconn(self.settings['network']['ip'], self.settings['network']['port'])
        self.DEMO_MODE = False
        if self.conn.checkConnection() != 0:
            self.DEMO_MODE = True
            self.conn.OFFLINE_MODE = True
            print("\nDemo mode entered")
        else:
            # if connection is present and no demo mode then create timer for connection checking
            connCheckTimer = QTimer()
            connCheckTimer.timeout.connect(self.connCheckTimerHandler)
            connCheckTimer.start(self.settings['network']['checkInterval'])  # every 5 seconds
            # also create handler function for connection lost (for example, when reading some coefficient from MCU)
            self.conn.connLost.signal.connect(self.connLostHandler)

        self.conn.saveCurrentValues()

        self.mainWindow = MainWindow(self)
        self.mainWindow.show()


    def connCheckTimerHandler(self):
        if self.conn.checkConnection():
            self.connLostHandler()
        else:
            if self.conn.OFFLINE_MODE:
                self.conn.OFFLINE_MODE = False
                self.mainWindow.centralWidget.refreshAllPIDvalues()
                self.mainWindow.statusBar().removeWidget(connLostStatusBarLabel)
                self.mainWindow.statusBar().showMessage('Reconnected')

    # handler function for connLost slot
    def connLostHandler(self):
        if not self.conn.OFFLINE_MODE:
            self.conn.OFFLINE_MODE = True
            self.mainWindow.statusBar().addWidget(connLostStatusBarLabel)
            MessageWindow(text='Connection was lost. App going to Offline mode and will be trying to reconnect', type='Warning')



if __name__ == '__main__':


    ORGANIZATION_NAME = 'Andrey Chufyrev'
    APPLICATION_NAME = 'PID controller GUI'
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    app = MainApplication(sys.argv)

    connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")

    sys.exit(app.exec_())
