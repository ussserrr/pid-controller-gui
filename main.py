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

        self.contValGroupBoxes = {
            'setpoint': ValueGroupBox('setpoint', app.conn),
            'Kp': ValueGroupBox('Kp', app.conn),
            'Ki': ValueGroupBox('Ki', app.conn),
            'Kd': ValueGroupBox('Kd', app.conn)
        }

        self.errorsSettingsWindow = ErrorsSettingsWindow(app)

        self.graphs = CustomGraphicsLayoutWidget(
            nPoints=app.settings['graphs']['numberOfPoints'],
            procVarRange=(0.0, 10.0),  # TODO: store as variables or make settings for these
            contOutRange=(0.0, 10.0),
            interval=app.settings['graphs']['updateInterval'],
            theme=app.settings['appearance']['theme'],
            start=False
        )

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

        # TODO: draw a scheme of this grid in documentation
        grid.addWidget(self.contValGroupBoxes['setpoint'], 0, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['Kp'], 3, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['Ki'], 6, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['Kd'], 9, 0, 3, 2)

        grid.addWidget(self.graphs, 0, 2, 14, 4)


        avrgUHBox = QHBoxLayout()
        avrgUHBox.addWidget(QLabel("Process Variable:"))
        avrgUHBox.addWidget(self.avrgULabel)
        grid.addLayout(avrgUHBox, 12, 0, 1, 2)

        avrgPIDHBox = QHBoxLayout()
        avrgPIDHBox.addWidget(QLabel("Controller Output:"))
        avrgPIDHBox.addWidget(self.avrgPIDLabel)
        grid.addLayout(avrgPIDHBox, 13, 0, 1, 2)


    def refreshAllPIDvalues(self):
        for groupBox in self.contValGroupBoxes.values():
            groupBox.refreshVal()
        # self.setpointGroupBox.refreshVal()
        # self.KpGroupBox.refreshVal()
        # self.KiGroupBox.refreshVal()
        # self.KdGroupBox.refreshVal()
        self.errorsSettingsWindow.updateDisplayingValues('PerrLimits', 'IerrLimits')


# TODO: move to MainWindow (where action resides)
# def restore(conn):
#     conn.restoreValues()
#     app.mainWindow.centralWidget.refreshAllPIDvalues()


# TODO: move to MainWindow (where action resides)
# TODO: maybe replace MessageWindows with StatusBar' messages
# def saveToEEPROM(conn):
#     if conn.saveToEEPROM() == 0:
#         MessageWindow(text='Successfully saved', type='Info')
#         app.mainWindow.centralWidget.refreshAllPIDvalues()
#     else:
#         MessageWindow(text='Saving failed!', type='Error')




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
        restoreValuesAction.triggered.connect(self.restoreContValues)

        saveToEEPROMAction = QAction(QIcon("img/eeprom.png"), 'Save to EEPROM', self)
        saveToEEPROMAction.setShortcut('S')
        saveToEEPROMAction.setStatusTip("[S] Save current controller configuration to EEPROM")
        saveToEEPROMAction.triggered.connect(self.saveToEEPROM)

        # TODO: rename 'cont' to something more distinguishable from 'conn'
        contToolbar = self.addToolBar('controller')  # internal name
        contToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        contToolbar.addAction(errorsLimitsAction)
        contToolbar.addAction(restoreValuesAction)
        contToolbar.addAction(saveToEEPROMAction)


        playpauseAction = QAction(QIcon('img/play_pause.png'), 'Play/Pause', self)
        playpauseAction.setShortcut('P')
        playpauseAction.setStatusTip('[P] Play/pause graphs')
        playpauseAction.triggered.connect(self.playpauseGraphs)

        graphsToolbar = self.addToolBar('graphs')
        graphsToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        graphsToolbar.addAction(playpauseAction)
        self.playpauseButton = graphsToolbar.widgetForAction(playpauseAction)
        self.playpauseButton.setCheckable(True)
        self.playpauseButton.setChecked(True)


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


    def restoreContValues(self):
        self.app.conn.restoreValues()
        self.centralWidget.refreshAllPIDvalues()


    def saveToEEPROM(self):
        if self.app.conn.saveToEEPROM() == 0:
            MessageWindow(text='Successfully saved', type='Info')
            self.app.mainWindow.centralWidget.refreshAllPIDvalues()
        else:
            MessageWindow(text='Saving failed!', type='Error')




class MainApplication(QApplication):
    # TODO: apply settings on-the-fly (not requiring a reboot)
    # TODO: add more ToolTips and StatusTips for elements

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
            self.connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")
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
                self.mainWindow.statusBar().removeWidget(self.connLostStatusBarLabel)
                self.mainWindow.statusBar().showMessage('Reconnected')

    # handler function for the connLost slot
    def connLostHandler(self):
        if not self.conn.OFFLINE_MODE:
            self.conn.OFFLINE_MODE = True
            self.mainWindow.statusBar().addWidget(self.connLostStatusBarLabel)
            MessageWindow(text='Connection was lost. App going to Offline mode and will be trying to reconnect', type='Warning')




if __name__ == '__main__':

    ORGANIZATION_NAME = 'Andrey Chufyrev'
    APPLICATION_NAME = 'PID controller GUI'
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    app = MainApplication(sys.argv)

    sys.exit(app.exec_())
