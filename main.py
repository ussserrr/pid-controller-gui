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

from PyQt5.QtCore import Qt, QCoreApplication, QT_VERSION_STR, QTimer, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QGridLayout, QHBoxLayout, QLabel, QAction
from PyQt5.QtGui import QIcon
from PyQt5.Qt import PYQT_VERSION_STR

import qdarkstyle

# local imports
import remotecontroller
import miscgraphics
import graphs
import settings
import errorssettings
import about




class CentralWidget(QWidget):
    """
    CentralWidget holds ValueGroupBox'es corresponding to PID setpoint and coefficients, live graphs and averaging
    labels
    """

    def __init__(self, app: QApplication, parent=None):
        """
        CentralWidget constructor

        :param app: parent MainApplication
        :param parent: [optional] parent class
        """

        super(CentralWidget, self).__init__(parent)

        self.errorsSettingsWindow = errorssettings.ErrorsSettingsWindow(app=app)

        self.contValGroupBoxes = [
            miscgraphics.ValueGroupBox('setpoint', float_fmt=app.settings['pid']['valueFormat'], controller=app.conn),
            miscgraphics.ValueGroupBox('kP', float_fmt=app.settings['pid']['valueFormat'], controller=app.conn),
            miscgraphics.ValueGroupBox('kI', float_fmt=app.settings['pid']['valueFormat'], controller=app.conn),
            miscgraphics.ValueGroupBox('kD', float_fmt=app.settings['pid']['valueFormat'], controller=app.conn)
        ]

        self.graphs = graphs.CustomGraphicsLayoutWidget(
            names=(app.settings['pid']['processVariable']['name'],
                   app.settings['pid']['controllerOutput']['name']),
            numPoints=app.settings['graphs']['numberOfPoints'],
            interval=app.settings['graphs']['updateInterval'],
            ranges=((app.settings['pid']['processVariable']['limits']['min'],
                     app.settings['pid']['processVariable']['limits']['max']),
                    (app.settings['pid']['controllerOutput']['limits']['min'],
                     app.settings['pid']['controllerOutput']['limits']['max'])),
            units=(app.settings['pid']['processVariable']['unit'],
                   app.settings['pid']['controllerOutput']['unit']),
            controlPipe=None if app.isOfflineMode else app.conn.input_thread_control_pipe_main,
            streamPipeRX=None if app.isOfflineMode else app.conn.stream.pipe_rx,
            theme=app.settings['appearance']['theme'],
        )

        grid = QGridLayout()
        self.setLayout(grid)

        # TODO: draw a scheme of this grid in documentation
        # https://stackoverflow.com/questions/5909873/how-can-i-pretty-print-ascii-tables-with-python
        for groupBox, y in zip(self.contValGroupBoxes.values(), [0,3,6,9]):
            grid.addWidget(groupBox, y, 0, 3, 2)

        for averageLabel, name, y in zip(self.graphs.averageLabels, self.graphs.names, [12,13]):
            hBox = QHBoxLayout()
            hBox.addWidget(QLabel(name))
            hBox.addWidget(averageLabel, alignment=Qt.AlignLeft)
            grid.addLayout(hBox, y, 0, 1, 2)

        grid.addWidget(self.graphs, 0, 2, 14, 4)


    def refreshContValues(self) -> None:
        """
        Retrieve all controller parameters and update corresponding GUI elements. Useful to apply after connection's
        breaks. This does not affect values saved during the app launch (RemoteController.save_current_values())

        :return: None
        """

        for groupBox in self.contValGroupBoxes.values():
            groupBox.refreshVal()

        self.errorsSettingsWindow.updateDisplayingValues('err_P_limits', 'err_I_limits')




class MainWindow(QMainWindow):
    """
    MainWindow contains of toolbar, status bar, menu. All other items are placed on a CentralWidget
    """

    def __init__(self, app: QApplication, parent=None):
        """
        MainWindow constructor

        :param app: parent MainApplication
        :param parent: [optional] parent class
        """

        super(MainWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle(QCoreApplication.applicationName())
        self.setWindowIcon(QIcon('img/icon.png'))


        self.centralWidget = CentralWidget(app=app)
        self.setCentralWidget(self.centralWidget)

        #
        # App Toolbar section
        #
        exitAction = QAction(QIcon('img/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip("[Ctrl+Q] Exit application")
        exitAction.triggered.connect(self.app.quit)

        infoAction = QAction(QIcon('img/info.png'), 'Info', self)  # see about.py
        infoAction.setShortcut('Ctrl+I')
        infoAction.setStatusTip("[Ctrl+I] Application Info & About")
        self.aboutWindow = about.AboutWindow(app)
        infoAction.triggered.connect(self.aboutWindow.show)

        settingsAction = QAction(QIcon('img/settings.png'), 'Settings', self)  # see settings.py
        settingsAction.setShortcut('Ctrl+P')
        settingsAction.setStatusTip("[Ctrl+P] Application Settings")
        self.settingsWindow = settings.SettingsWindow(app=app)
        settingsAction.triggered.connect(self.settingsWindow.show)

        appToolbar = self.addToolBar('app')
        appToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        appToolbar.addAction(exitAction)
        appToolbar.addAction(infoAction)
        appToolbar.addAction(settingsAction)

        #
        # Controller Toolbar section
        #
        errorsLimitsAction = QAction(QIcon('img/set_errors.png'), 'Errors limits', self)  # see errorssettings.py
        errorsLimitsAction.setShortcut('E')
        errorsLimitsAction.setStatusTip("[E] Set values of errors limits")
        errorsLimitsAction.triggered.connect(self.centralWidget.errorsSettingsWindow.show)

        restoreValuesAction = QAction(QIcon('img/restore.png'), 'Restore controller', self)
        restoreValuesAction.setShortcut('R')
        restoreValuesAction.setStatusTip("[R] Restore all controller parameters to values at the program start time")
        restoreValuesAction.triggered.connect(self.restoreContValues)

        saveToEEPROMAction = QAction(QIcon('img/eeprom.png'), 'Save to EEPROM', self)
        saveToEEPROMAction.setShortcut('S')
        saveToEEPROMAction.setStatusTip("[S] Save current controller configuration to EEPROM")
        saveToEEPROMAction.triggered.connect(self.saveToEEPROM)

        # TODO: rename 'cont' to something more distinguishable from 'conn'
        contToolbar = self.addToolBar('controller')  # internal name
        contToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        contToolbar.addAction(errorsLimitsAction)
        contToolbar.addAction(restoreValuesAction)
        contToolbar.addAction(saveToEEPROMAction)

        #
        # Graphs Toolbar section
        #
        playpauseAction = QAction(QIcon('img/play_pause.png'), 'Play/Pause', self)
        playpauseAction.setShortcut('P')
        playpauseAction.setStatusTip("[P] Play/pause graphs")
        playpauseAction.triggered.connect(self.playpauseGraphs)

        graphsToolbar = self.addToolBar('graphs')
        graphsToolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        graphsToolbar.addAction(playpauseAction)
        self.playpauseButton = graphsToolbar.widgetForAction(playpauseAction)
        self.playpauseButton.setCheckable(True)
        self.playpauseButton.setChecked(True)
        self.graphsWereRun = False


        mainMenu = self.menuBar().addMenu('&Menu')
        mainMenu.addAction(exitAction)
        mainMenu.addAction(infoAction)
        mainMenu.addAction(settingsAction)


        if self.app.isOfflineMode:
            self.statusBar().addWidget(QLabel("<font color='red'>Offline mode</font>"))


    def playpauseGraphs(self) -> None:
        """
        Smartly toggles the state of live graphs

        :return: None
        """

        if self.centralWidget.graphs.isRun:
            self.playpauseButton.setChecked(True)
        else:
            self.playpauseButton.setChecked(False)
        self.app.conn.stream.toggle()
        self.centralWidget.graphs.toggle()


    def restoreContValues(self) -> None:
        """
        Write PID parameters stored at program start to the controller

        :return: None
        """

        self.app.conn.restore_values(self.app.conn.snapshots[0])  # currently save and use only one snapshot
        self.centralWidget.refreshContValues()


    def saveToEEPROM(self) -> None:
        """
        Initiate writing of current parameters to the controller's EEPROM

        :return: None
        """

        if self.app.conn.save_to_eeprom() == remotecontroller.result['ok']:
            miscgraphics.MessageWindow("Successfully saved", status='Info')
            self.app.mainWindow.centralWidget.refreshContValues()
        else:
            miscgraphics.MessageWindow("Saving failed!", status='Error')


    def hideEvent(self, *args, **kwargs) -> None:
        """
        Detect window hide event to perform necessary actions. Modern OSes put minimized DE applications into some kind
        of 'sleep' mode to optimize its own performance and energy consumption. This leads to, for example, QT timers to
        be slow down and so on. And it may lead to some violations in a work flow such as connection breaks and stream
        overflows. So it better to 'freeze' any network and graphical activity during such period and then smoothly
        resume it when needed. The user doesn't stare at the application, anyway :)

        Note: this doesn't include simple moving a window to the background (e.g. overlapping by another window)

        :param args: positional arguments passing directly to the base-class function
        :param kwargs: keyword arguments passing directly to the base-class function
        :return: None
        """

        # 1. stop the connection check timer
        if not self.app.isOfflineMode:
            self.app.connCheckTimer.stop()

        # 2. stop live plots (it stops both the stream and graphs)
        if self.centralWidget.graphs.isRun:
            self.playpauseGraphs()
            self.graphsWereRun = True
        else:
            self.graphsWereRun = False

        # 3. in the end block the listening section of the input thread (to prevent pipes overflows)
        self.app.conn.pause()

        # finally, call the base class' method
        super(MainWindow, self).hideEvent(*args, **kwargs)


    def showEvent(self, *args, **kwargs) -> None:
        """
        Detect window show event to perform necessary actions. Modern OSes put minimized DE applications into some kind
        of 'sleep' mode to optimize its own performance and energy consumption. This leads to, for example, QT timers to
        be slow down and so on. And it may lead to some violations in a work flow such as connection breaks and stream
        overflows. So it better to 'freeze' any network and graphical activity during such period and then smoothly
        resume it when needed. The user doesn't stare at the application, anyway :)

        Note: this doesn't include simple moving a window to the background (e.g. overlapping by another window)

        :param args: positional arguments passing directly to the base-class function
        :param kwargs: keyword arguments passing directly to the base-class function
        :return: None
        """

        # 1. resume the listening section of the input thread first
        self.app.conn.resume()

        # 2. start the connection check timer
        if not self.app.isOfflineMode:
            self.app.connCheckTimer.start(self.app.settings['network']['checkInterval'])

        # 3. re-run graphs if they were in run
        if self.graphsWereRun:
            self.playpauseGraphs()

        # finally, call the base class' method
        super(MainWindow, self).showEvent(*args, **kwargs)


    def closeEvent(self, event) -> None:
        """
        Catch the window close event - interpret it the same as an application termination

        :param event: QT event
        :return: None
        """

        self.hide()
        self.app.quit()




class MainApplication(QApplication):
    """
    Customized QApplication - entry point of the whole program
    """

    # TODO: apply settings on-the-fly (not requiring a reboot)
    # TODO: add more ToolTips and StatusTips for elements
    # TODO: list all used packets in 'about' (qdarkstyle, icons, etc.)


    connLostSignal = pyqtSignal()  # must be part of the class definition and cannot be dynamically added after


    def __init__(self, argv: list):
        """
        MainApplication constructor

        :param argv: the list of command line arguments passed to a Python script
        """

        super(MainApplication, self).__init__(argv)


        self.settings = settings.Settings(defaults='defaultSettings.json')  # settings [customized] dictionary

        # TODO: add logging maybe

        if self.settings['appearance']['theme'] == 'dark':
            # TODO: warns itself as a deprecated method though no suitable alternative has been suggested
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())


        # show this when the connection is broken
        self.connLostStatusBarLabel = QLabel("<font color='red'>Connection was lost. Trying to reconnect...</font>")
        # Also create a handler function for connection breaks (for example, when break is occur during the read of
        # some coefficient from the controller)
        self.connLostSignal.connect(self.connLostHandler)

        self.isOfflineMode = False

        self.conn = remotecontroller.RemoteController(
            self.settings['network']['ip'],
            self.settings['network']['port'],
            conn_lost_signal=self.connLostSignal
        )

        # RemoteController' self-check determines the state of the connection. Such app state determined during the
        # startup process will remain during all following activities (i.e. app enters the demo mode) and can be changed
        # only after the restart
        if self.conn.is_offline_mode:
            self.isOfflineMode = True
            print("Offline mode")
            miscgraphics.MessageWindow("No connection to the remote controller. App goes to the Offline (demo) mode. "
                                "All values are random. To try to reconnect please restart the app", status='Warning')

        else:
            # If connection is present (so no demo mode is needed) then create the timer for connection checking. It
            # will start on MainWindow' show
            self.connCheckTimer = QTimer()
            self.connCheckTimer.timeout.connect(self.connCheckTimerHandler)

        self.conn.save_current_values()


        # We can create the MainWindow only after instantiating the RemoteController because it is used for obtaining
        # values and setting parameters
        self.mainWindow = MainWindow(app=self)
        self.mainWindow.show()


    def quit(self) -> None:
        """
        QApplication quit method

        :return: None
        """

        self.conn.close()

        super(MainApplication, self).quit()


    def connCheckTimerHandler(self) -> None:
        """
        Procedure to invoke for connection checking

        :return: None
        """

        print("Check connection")

        if self.conn.check_connection() == remotecontroller.result['error']:
            self.connLostHandler()
        else:
            # prevent of multiple calls of these instructions by using this flag
            if self.isOfflineMode:
                self.isOfflineMode = False
                print('Reconnected')
                self.mainWindow.centralWidget.refreshContValues()
                self.mainWindow.statusBar().removeWidget(self.connLostStatusBarLabel)
                self.mainWindow.statusBar().showMessage('Reconnected')


    @pyqtSlot()
    def connLostHandler(self) -> None:
        """
        Slot corresponding to MainApplication.connLostSignal (typically emitted from RemoteController on unsuccessful
        read/write operations). Can also be called directly to handle connection break case

        :return: None
        """

        if not self.isOfflineMode:
            self.isOfflineMode = True
            print("Connection lost")
            try:
                if self.mainWindow.centralWidget.graphs.isRun:
                    self.mainWindow.playpauseGraphs()
                self.mainWindow.statusBar().addWidget(self.connLostStatusBarLabel)
                miscgraphics.MessageWindow("Connection was lost. The app goes to the Offline mode and will be trying "
                                           "to reconnect", status='Warning')

            # This exception is met when the RemoteController.check_connection() test has been passed but following
            # read/write operations cannot be successfully performed due to small corresponding timeouts. Then, connLost
            # signal is emitting. Since the RemoteController initialization has not been complete MainWindow certainly
            # has not been instantiated yet and so we will catch this exception. We can simply ignore such case and just
            # quietly mark the connection as offline without any notifications toward the user
            except AttributeError:
                print("Too small timeout")
                miscgraphics.MessageWindow("It seems like the connection is present but specified read/write timeouts "
                                           "is too small. Consider to fix your network or edit timeouts to match your "
                                           f"timings (see '{remotecontroller.__name__}.py' module).", status='Warning')




if __name__ == '__main__':
    """
    Main entry point
    """

    QCoreApplication.setOrganizationName("Andrey Chufyrev")
    QCoreApplication.setApplicationName("PID controller GUI")

    application = MainApplication(sys.argv)

<<<<<<< HEAD
    sys.exit(app.exec_())
>>>>>>> 9a70e43... initial commit
=======
    sys.exit(application.exec_())
>>>>>>> 57670f2... documentation 6, GUI fixes
