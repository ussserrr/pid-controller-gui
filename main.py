<<<<<<< HEAD
import sys
import os

from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton, \
    QApplication, QSpinBox, QStatusBar, QProgressBar, QLineEdit, QCheckBox, QGridLayout, \
    QTabWidget, QMainWindow, QToolTip, QAction, QLayout, QSizePolicy, QButtonGroup
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QCoreApplication, QSettings, Qt, QT_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR
import qdarkstyle

from miscgraphics import MessageWindow, ValueGroupBox, CustomGraphicsLayoutWidget
from remotecontroller import RemoteController
from settings import Settings, SettingsWindow
from errorssettings import ErrorsSettingsWindow
from about import AboutWindow

# TODO: rename all 'procVar_' and 'contOut_' to 'pv_', 'co_'. Maybe use _docstring_ for entire module to declare the glossary



class CentralWidget(QWidget):

    def __init__(self, app, parent=None):
        super(CentralWidget, self).__init__(parent)

        self.app = app

        self.contValGroupBoxes = {
            'setpoint': ValueGroupBox('setpoint', app.conn),
            'kP': ValueGroupBox('kP', app.conn),
            'kI': ValueGroupBox('kI', app.conn),
            'kD': ValueGroupBox('kD', app.conn)
        }

        self.errorsSettingsWindow = ErrorsSettingsWindow(app)

        self.graphs = CustomGraphicsLayoutWidget(
            nPoints=app.settings['graphs']['numberOfPoints'],
            procVarRange=(-2.0, 2.0),  # TODO: store as variables or make settings for these
            contOutRange=(-2.0, 2.0),
            interval=app.settings['graphs']['updateInterval'],
            stream_pipe_rx=None if self.app.isOfflineMode else self.app.conn.stream.pipe_rx,
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
        # https://stackoverflow.com/questions/5909873/how-can-i-pretty-print-ascii-tables-with-python
        grid.addWidget(self.contValGroupBoxes['setpoint'], 0, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kP'], 3, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kI'], 6, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kD'], 9, 0, 3, 2)

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
        self.errorsSettingsWindow.updateDisplayingValues('err_P_limits', 'err_I_limits')




# TODO: maybe replace MessageWindows with StatusBar' messages
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

        if self.app.isOfflineMode:
            self.statusBar().addWidget(QLabel("<font color='red'>Offline mode</font>"))


    def playpauseGraphs(self):
        if self.centralWidget.graphs.isRun:
            self.playpauseButton.setChecked(True)
        else:
            self.playpauseButton.setChecked(False)
        self.app.conn.stream.toggle()
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


    def closeEvent(self, QCloseEvent):
        self.app.quit()




class MainApplication(QApplication):
    # TODO: apply settings on-the-fly (not requiring a reboot)
    # TODO: add more ToolTips and StatusTips for elements

    def __init__(self, argv, thread_pid=None):
        super(MainApplication, self).__init__(argv)

        self.settings = Settings(defaults='defaultSettings.json')

        if self.settings['appearance']['theme'] == 'dark':
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")

        self.isOfflineMode = False
        self.conn = RemoteController(self.settings['network']['ip'], self.settings['network']['port'],
                                     thread_pid=thread_pid)
        if self.conn.isOfflineMode:
            self.isOfflineMode = True
            print("offline mode")
            MessageWindow(text="No connection to the remote controller. App goes to the Offline (demo) mode. "
                               "All values are random. To try to reconnect please restart the app", type='Warning')
        else:
            # if connection is present and no demo mode then create timer for connection checking
            self.connCheckTimer = QTimer()
            self.connCheckTimer.timeout.connect(self.connCheckTimerHandler)
            self.connCheckTimer.start(self.settings['network']['checkInterval'])  # every 5 seconds
            # also create handler function for connection lost (for example, when reading some coefficient from MCU)
            self.conn.connLost.signal.connect(self.connLostHandler)

        self.conn.saveCurrentValues()

        # self.test_timer = QTimer()
        # self.test_timer.timeout.connect(self.test)
        # self.test_timer.start(500)  # every 5 seconds

        self.mainWindow = MainWindow(self)
        self.mainWindow.show()


    def test(self):
        print("read all")
        self.conn.saveCurrentValues()


    def quit(self):
        self.conn.close()
        # print(f"pipe: {self.mainWindow.centralWidget.graphs.cnt}")
        super(MainApplication, self).quit()


    def connCheckTimerHandler(self):
        print("check connection")
        if self.conn.checkConnection() != 0:
            self.connLostHandler()
        else:
            if self.isOfflineMode:
                self.isOfflineMode = False
                self.mainWindow.centralWidget.refreshAllPIDvalues()
                self.mainWindow.statusBar().removeWidget(self.connLostStatusBarLabel)
                self.mainWindow.statusBar().showMessage('Reconnected')


    # handler function for the connLost slot
    def connLostHandler(self):
        if not self.isOfflineMode:
            self.isOfflineMode = True
            print('lost connection')
            # if self.mainWindow.centralWidget.graphs.isRun:
            #     self.mainWindow.playpauseGraphs()
            self.mainWindow.statusBar().addWidget(self.connLostStatusBarLabel)
            MessageWindow(text="Connection was lost. App goes to the Offline mode and will be trying to reconnect",
                          type='Warning')  # TODO: stop stream on controller if no 'ping' messages




if __name__ == '__main__':
    ORGANIZATION_NAME = 'Andrey Chufyrev'
    APPLICATION_NAME = 'PID controller GUI'
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    main_thread_pid = os.getpid()
    app = MainApplication(sys.argv, thread_pid=main_thread_pid)

    sys.exit(app.exec_())
=======
import sys

from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton, \
    QApplication, QSpinBox, QStatusBar, QProgressBar, QLineEdit, QCheckBox, QGridLayout, \
    QTabWidget, QMainWindow, QToolTip, QAction, QLayout, QSizePolicy, QButtonGroup
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QCoreApplication, QSettings, Qt, QT_VERSION_STR, pyqtSlot, pyqtSignal
from PyQt5.Qt import PYQT_VERSION_STR

import qdarkstyle

# local imports
import remotecontroller
import miscgraphics
import graphs
import settings
import errorssettings
from about import AboutWindow

# TODO: rename all 'procVar_' and 'contOut_' to 'pv_', 'co_'. Maybe use _docstring_ for entire module to declare the glossary



class CentralWidget(QWidget):

    def __init__(self, app, parent=None):
        super(CentralWidget, self).__init__(parent)

        self.app = app

        self.contValGroupBoxes = {
            'setpoint': miscgraphics.ValueGroupBox('setpoint', app.conn),
            'kP': miscgraphics.ValueGroupBox('kP', app.conn),
            'kI': miscgraphics.ValueGroupBox('kI', app.conn),
            'kD': miscgraphics.ValueGroupBox('kD', app.conn)
        }

        self.errorsSettingsWindow = errorssettings.ErrorsSettingsWindow(app)

        self.graphs = graphs.CustomGraphicsLayoutWidget(
            nPoints=app.settings['graphs']['numberOfPoints'],
            interval=app.settings['graphs']['updateInterval'],
            procVarRange=(-2.0, 2.0),  # TODO: store as variables or make settings for these
            contOutRange=(-2.0, 2.0),
            controlPipe=None if self.app.isOfflineMode else self.app.conn.input_thread_control_pipe_main,
            streamPipeRX=None if self.app.isOfflineMode else self.app.conn.stream.pipe_rx,
            theme=app.settings['appearance']['theme'],
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
        # https://stackoverflow.com/questions/5909873/how-can-i-pretty-print-ascii-tables-with-python
        grid.addWidget(self.contValGroupBoxes['setpoint'], 0, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kP'], 3, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kI'], 6, 0, 3, 2)
        grid.addWidget(self.contValGroupBoxes['kD'], 9, 0, 3, 2)

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
        self.errorsSettingsWindow.updateDisplayingValues('err_P_limits', 'err_I_limits')




# TODO: maybe replace MessageWindows with StatusBar' messages
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
        self.settingsWindow = settings.SettingsWindow(app)
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
        self.graphsWasRun = False

        mainMenu = self.menuBar().addMenu('&Menu')
        mainMenu.addAction(exitAction)
        mainMenu.addAction(infoAction)
        mainMenu.addAction(settingsAction)

        if self.app.isOfflineMode:
            self.statusBar().addWidget(QLabel("<font color='red'>Offline mode</font>"))


    def playpauseGraphs(self):
        if self.centralWidget.graphs.isRun:
            self.playpauseButton.setChecked(True)
        else:
            self.playpauseButton.setChecked(False)
        self.app.conn.stream.toggle()
        self.centralWidget.graphs.toggle()


    def restoreContValues(self):
        self.app.conn.restore_values(self.app.conn.snapshots[0])
        self.centralWidget.refreshAllPIDvalues()


    def saveToEEPROM(self):
        if self.app.conn.save_to_eeprom() == remotecontroller.result['ok']:
            miscgraphics.MessageWindow('Successfully saved', status='Info')
            self.app.mainWindow.centralWidget.refreshAllPIDvalues()
        else:
            miscgraphics.MessageWindow('Saving failed!', status='Error')


    def hideEvent(self, *args, **kwargs):
        print("The app has been hide")
        if not self.app.isOfflineMode:
            self.app.connCheckTimer.stop()
        if self.centralWidget.graphs.isRun:
            self.playpauseGraphs()
            self.graphsWasRun = True
        else:
            self.graphsWasRun = False
        self.app.conn.pause()
        super(MainWindow, self).hideEvent(*args, **kwargs)


    def showEvent(self, *args, **kwargs):
        print("The app has been restored")
        self.app.conn.resume()
        if not self.app.isOfflineMode:
            self.app.connCheckTimer.start(self.app.settings['network']['checkInterval'])
        if self.graphsWasRun:
            self.playpauseGraphs()
        super(MainWindow, self).showEvent(*args, **kwargs)


    def closeEvent(self, QCloseEvent):
        self.app.quit()




class MainApplication(QApplication):
    # TODO: apply settings on-the-fly (not requiring a reboot)
    # TODO: add more ToolTips and StatusTips for elements

    connLostSignal = pyqtSignal()

    def __init__(self, argv):
        super(MainApplication, self).__init__(argv)

        self.settings = settings.Settings(defaults='defaultSettings.json')

        if self.settings['appearance']['theme'] == 'dark':
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        # self.connLostSignal = pyqtSignal()
        self.connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")

        self.isOfflineMode = False
        self.conn = remotecontroller.RemoteController(
            self.settings['network']['ip'],
            self.settings['network']['port'],
            conn_lost_signal=self.connLostSignal
        )
        if self.conn.is_offline_mode:
            self.isOfflineMode = True
            print("offline mode")
            miscgraphics.MessageWindow("No connection to the remote controller. App goes to the Offline (demo) mode. "
                               "All values are random. To try to reconnect please restart the app", status='Warning')
        else:
            # if connection is present and no demo mode then create timer for connection checking
            self.connCheckTimer = QTimer()
            self.connCheckTimer.timeout.connect(self.connCheckTimerHandler)
            # self.connCheckTimer.start(self.settings['network']['checkInterval'])  # every 5 seconds
            # also create handler function for connection lost (for example, when reading some coefficient from MCU)
            self.connLostSignal.connect(self.connLostHandler)

        self.conn.save_current_values()

        self.mainWindow = MainWindow(self)
        self.mainWindow.show()


    def quit(self):
        self.conn.close()
        # print(f"pipe: {self.mainWindow.centralWidget.graphs.points_cnt}")
        super(MainApplication, self).quit()


    def connCheckTimerHandler(self):
        print("check connection")
        if self.conn.check_connection() != 0:
            self.connLostHandler()
        else:
            if self.isOfflineMode:
                self.isOfflineMode = False
                print("reconnected")
                self.mainWindow.centralWidget.refreshAllPIDvalues()
                self.mainWindow.statusBar().removeWidget(self.connLostStatusBarLabel)
                self.mainWindow.statusBar().showMessage('Reconnected')


    # handler function for the connLost slot
    @pyqtSlot()
    def connLostHandler(self):
        # TODO: exception: MainApplication has no attribute mainWindow
        if not self.isOfflineMode:
            self.isOfflineMode = True
            print('lost connection')
            if self.mainWindow.centralWidget.graphs.isRun:
                self.mainWindow.playpauseGraphs()
            self.mainWindow.statusBar().addWidget(self.connLostStatusBarLabel)
            miscgraphics.MessageWindow("Connection was lost. The app goes to the Offline mode and will be trying to reconnect",
                                       status='Warning')




if __name__ == '__main__':

    QCoreApplication.setOrganizationName("Andrey Chufyrev")
    QCoreApplication.setApplicationName("PID controller GUI")

    app = MainApplication(sys.argv)

    sys.exit(app.exec_())
>>>>>>> 9a70e43... initial commit
