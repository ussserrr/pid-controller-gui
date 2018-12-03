"""
Docstring
"""

import functools

from PyQt5.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, \
                            QStatusBar
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5.QtCore import QTimer, QEvent

# local imports
import remotecontroller



STATUSBAR_MSG_TIMEOUT = 5000



class ErrorsSettingsWindow(QWidget):
    """
    Window to control PID components errors (proportional and integral). QStatusBar is used to display service messages
    """

    def __init__(self, app, parent=None):
        """
        ErrorsSettingsWindow constructor

        :param app: parent MainApplication instance
        :param parent: [optional] parent class
        """

        super(ErrorsSettingsWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle("PID errors settings")
        self.setWindowIcon(QIcon('img/set_errors.png'))

        grid = QGridLayout()
        self.setLayout(grid)


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


        for key, name in (('err_P_limits', "P error limits"),
                          ('err_I_limits', "I error limits")):

            setButton = QPushButton('Set')
            setButton.clicked.connect(functools.partial(self.setErrLimits, key))

            hBox = QHBoxLayout()
            hBox.addWidget(QLabel("Min:"))
            hBox.addWidget(self.lineEdits[key]['min'])
            hBox.addWidget(QLabel("Max:"))
            hBox.addWidget(self.lineEdits[key]['max'])
            hBox.addWidget(setButton)

            groupBox = QGroupBox(name)

            if key == 'err_I_limits':
                self.resetButton = QPushButton("Reset I error")
                self.resetButton.clicked.connect(self.resetIerr)
                self.event(QEvent(QEvent.ToolTip))

                hBox2 = QHBoxLayout()
                hBox2.addWidget(self.resetButton)

                vBox = QVBoxLayout()
                vBox.addLayout(hBox)
                vBox.addLayout(hBox2)

                groupBox.setLayout(vBox)

            else:
                groupBox.setLayout(hBox)

            grid.addWidget(groupBox)


        self.statusBar = QStatusBar()
        grid.addWidget(self.statusBar)


    def event(self, event: QEvent) -> bool:
        """
        Overridden method is used to catch QEvent.ToolTip to display current value

        :param event: QEvent instance
        :return: bool
        """

        if event.type() == QEvent.ToolTip:
            self.resetButton.setToolTip(f"Current I error: " +
                                        self.app.settings['pid']['valueFormat'].format(self.app.conn.read('err_I')))

        return super(ErrorsSettingsWindow, self).event(event)


    def show(self):
        """
        Overridden method to update displaying widgets before showing the window itself

        :return: None
        """

        # self.updateDisplayingValues('err_P_limits', 'err_I_limits')

        super(ErrorsSettingsWindow, self).show()


    def removeStatusBarWidget(self, widget) -> None:
        """
        Callback function to remove given widget from the status bar after timeout

        :param widget: widget to remove
        :return: None
        """

        self.statusBar.removeWidget(widget)


    def updateDisplayingValues(self, *what) -> None:
        """
        Refresh one or more widgets displaying values

        :param what: strings representing values names that need to be updated
        :return: None
        """

        for item in what:
            valMin, valMax = self.app.conn.read(item)
            self.lineEdits[item]['min'].setText(self.app.settings['pid']['valueFormat'].format(valMin))
            self.lineEdits[item]['max'].setText(self.app.settings['pid']['valueFormat'].format(valMax))


    def setErrLimits(self, what: str) -> None:
        """
        'Set' button clicked slot

        :param what: string representing PID component error to set (proportional or integral)
        :return: None
        """

        try:
            # QDoubleValidator doesn't work in combine with explicitly set value
            valMin = float(self.lineEdits[what]['min'].text())
            valMax = float(self.lineEdits[what]['max'].text())
        except ValueError:  # user enters not valid number or NaN
            pass
        else:
            if valMax < valMin:
                resultLabel = QLabel("<font color='red'>Upper limit value is less than lower</font>")
            else:
                self.app.conn.write(what, valMin, valMax)
                resultLabel = QLabel('Success')
            self.statusBar.addWidget(resultLabel)
            QTimer().singleShot(STATUSBAR_MSG_TIMEOUT, functools.partial(self.removeStatusBarWidget, resultLabel))

        self.updateDisplayingValues(what)


    def resetIerr(self) -> None:
        """
        Set integral PID component to 0

        :return: None
        """

        if self.app.conn.reset_i_err() == remotecontroller.result['ok']:
            statusLabel = QLabel("I error has been reset")
        else:
            statusLabel = QLabel("<font color='red'>I error reset failed</font>")
        self.statusBar.addWidget(statusLabel)
        QTimer().singleShot(STATUSBAR_MSG_TIMEOUT, functools.partial(self.removeStatusBarWidget, statusLabel))
