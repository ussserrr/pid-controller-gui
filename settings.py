"""
settings.py - way to settings managing, both internal and graphical


Settings
    dict subclass with the additional interface to QSettings for handling both run-time and non-volatile settings

SettingsWindow
    GUI to let a user edit the settings
"""

import copy
import json
import ipaddress

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QRadioButton, QLabel, QStyle, \
    QPushButton, QLineEdit, QSpinBox, QButtonGroup

# local imports
import miscgraphics



class Settings(dict):
    """
    Easier way to manage different parameters. Briefly speaking it combines conventional dictionary with the additional
    interface to QSettings via 'persistentStorage' property
    """

    def __init__(self, defaults: str='defaultSettings.json'):
        """
        Settings constructor. Automatically retrieving settings from the persistent storage if they are present

        :param defaults: path to default settings JSON file
        """

        super(Settings, self).__init__()

        with open(defaults, mode='r') as defaultSettingsJSONFile:
            self.defaults = json.load(defaultSettingsJSONFile)

        self.persistentStorage = QSettings()
        self._retrieve()


    def _retrieve(self) -> None:
        """
        Determines whether settings are present in the system storage and based on that decides what to choose

        :return: None
        """

        # It seems like QT or OS stores additional parameters unwanted for us (at least on macOS) so we isolate our
        # storage using 'app' group
        self.persistentStorage.beginGroup('app')

        if not self.persistentStorage.contains('settings'):
            print("No settings, clear all, use default...")
            self.persistentStorage.endGroup()
            self.persistentStorage.clear()

            # update() is the inherited method of the dictionary to update its items. We assume that 'defaults' will not
            # change but for a confidence we make a copy
            self.update(copy.deepcopy(self.defaults))
            # self.save(self.defaults)

        else:
            print("Restore from NV-storage")
            self.update(self.persistentStorage.value('settings', type=dict))
            self.persistentStorage.endGroup()


    def save(self, settings: dict) -> None:
        """
        Push settings from the given dictionary to the persistent storage

        :param settings: dictionary containing settings. Any subclass including this can be passed as well
        :return: None
        """

        print("Saving settings...")
        self.persistentStorage.beginGroup('app')
        self.persistentStorage.setValue('settings', copy.deepcopy(settings))
        self.persistentStorage.endGroup()


    def __deepcopy__(self, memodict={}) -> dict:
        """
        As this class contains additional properties such as QSettings that we don't want to be copied we need to
        override __deepcopy__ method

        :param memodict: see deepcopy docs, not used in our case
        :return: copied dictionary

        """

        # inner instruction makes temporary shallow copy of the dictionary (without custom options) and outer is
        # performing an actual deep-copying
        return copy.deepcopy(dict(self))



class SettingsWindow(QWidget):
    """
    Window to edit some parameters of network connection, visual appearance and so on. Actual saving is performing
    during the close event
    """

    def __init__(self, app, parent=None):
        """
        SettingsWindow constructor

        :param app: parent MainApplication instance
        :param parent: [optional] parent class
        """

        super(SettingsWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle('Settings')
        self.setWindowIcon(QIcon('img/settings.png'))

        #
        # Network section
        #
        networkGroupBox = QGroupBox("Controller connection")
        networkVBox = QVBoxLayout()
        networkGroupBox.setLayout(networkVBox)

        networkHBox1 = QHBoxLayout()
        self.ipLineEdit = QLineEdit()
        self.ipLineEdit.setInputMask("000.000.000.000;_")
        self.portLineEdit = QLineEdit()
        self.portLineEdit.setValidator(QIntValidator(0, 65535))
        networkHBox1.addWidget(QLabel("IP address:"))
        networkHBox1.addWidget(self.ipLineEdit)
        networkHBox1.addWidget(QLabel("UDP port:"))
        networkHBox1.addWidget(self.portLineEdit)

        networkHBox2 = QHBoxLayout()
        self.connCheckIntervalSpinBox = QSpinBox()
        self.connCheckIntervalSpinBox.setSuffix(" ms")
        self.connCheckIntervalSpinBox.setMinimum(10)
        self.connCheckIntervalSpinBox.setMaximum(1e9)
        self.connCheckIntervalSpinBox.setSingleStep(1000)
        networkHBox2.addWidget(QLabel("Checks interval:"))
        networkHBox2.addWidget(self.connCheckIntervalSpinBox)

        networkVBox.addLayout(networkHBox1)
        networkVBox.addLayout(networkHBox2)

        #
        # Appearance section
        #
        themeGroupBox = QGroupBox('Theme')
        themeHBox = QHBoxLayout()
        themeGroupBox.setLayout(themeHBox)

        self.themeLightRadioButton = QRadioButton('Light')
        self.themeDarkRadioButton = QRadioButton('Dark')
        themeButtonGroup = QButtonGroup(themeGroupBox)
        themeButtonGroup.addButton(self.themeLightRadioButton)
        themeButtonGroup.addButton(self.themeDarkRadioButton)

        themeHBox.addWidget(self.themeLightRadioButton)
        themeHBox.addWidget(self.themeDarkRadioButton)

        #
        # Graphs section
        #
        graphsGroupBox = QGroupBox('Graphics')
        graphsVBox = QVBoxLayout()
        graphsGroupBox.setLayout(graphsVBox)

        graphsHBox1 = QHBoxLayout()
        self.graphsUpdateIntervalSpinBox = QSpinBox()
        self.graphsUpdateIntervalSpinBox.setSuffix(' ms')
        self.graphsUpdateIntervalSpinBox.setMinimum(1)
        self.graphsUpdateIntervalSpinBox.setMaximum(1e9)
        self.graphsUpdateIntervalSpinBox.setSingleStep(10)
        graphsHBox1.addWidget(QLabel("Update interval:"))
        graphsHBox1.addWidget(self.graphsUpdateIntervalSpinBox)

        graphsHBox2 = QHBoxLayout()
        self.graphsNumberOfPointsSpinBox = QSpinBox()
        self.graphsNumberOfPointsSpinBox.setMinimum(3)
        self.graphsNumberOfPointsSpinBox.setMaximum(1e5)
        self.graphsNumberOfPointsSpinBox.setSingleStep(50)
        graphsHBox2.addWidget(QLabel("Number of points:"))
        graphsHBox2.addWidget(self.graphsNumberOfPointsSpinBox)

        graphsVBox.addLayout(graphsHBox1)
        graphsVBox.addLayout(graphsHBox2)

        # reset to defaults
        resetSettingsButton = QPushButton(QIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton)),
                                          "Reset to defaults")
        resetSettingsButton.clicked.connect(self.resetSettings)

        # get all values for the first time
        self.updateDisplayingValues()

        # widget layout - grid
        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(themeGroupBox)
        grid.addWidget(networkGroupBox)
        grid.addWidget(graphsGroupBox)
        grid.addWidget(resetSettingsButton)


    def updateDisplayingValues(self) -> None:
        """
        Using global app settings class property to set all widgets to its values

        :return: None
        """

        self.ipLineEdit.setText(self.app.settings['network']['ip'])
        self.portLineEdit.setText(str(self.app.settings['network']['port']))
        self.connCheckIntervalSpinBox.setValue(self.app.settings['network']['checkInterval'])
        if self.app.settings['appearance']['theme'] == 'light':
            self.themeLightRadioButton.setChecked(True)
        else:
            self.themeDarkRadioButton.setChecked(True)
        self.graphsUpdateIntervalSpinBox.setValue(self.app.settings['graphs']['updateInterval'])
        self.graphsNumberOfPointsSpinBox.setValue(self.app.settings['graphs']['numberOfPoints'])


    def show(self):
        """
        Overridden method to refresh all values on each window show

        :return: None
        """

        self.settingsAtStart = copy.deepcopy(self.app.settings)
        self.updateDisplayingValues()

        super(SettingsWindow, self).show()


    def closeEvent(self, event):
        """
        Save settings on each window close. Before that we can edit parameters as we want to

        :param event: QT event
        :return: None
        """

        self.saveSettings()
        super(SettingsWindow, self).closeEvent(event)


    def saveSettings(self) -> None:
        """
        Parse, check and save the settings into the persistent storage associated with a self.app.settings instance

        :return: None
        """

        errors = []

        try:
            ipaddress.ip_address(self.ipLineEdit.text())
            self.app.settings['network']['ip'] = self.ipLineEdit.text()
        except ValueError:
            errors.append('IP address')

        try:
            self.app.settings['network']['port'] = int(self.portLineEdit.text())
        except ValueError:
            errors.append('UDP port')

        self.app.settings['network']['checkInterval'] = self.connCheckIntervalSpinBox.value()
        if self.themeLightRadioButton.isChecked():
            self.app.settings['appearance']['theme'] = 'light'
        else:
            self.app.settings['appearance']['theme'] = 'dark'
        self.app.settings['graphs']['updateInterval'] = int(self.graphsUpdateIntervalSpinBox.value())
        self.app.settings['graphs']['numberOfPoints'] = int(self.graphsNumberOfPointsSpinBox.value())


        if self.app.settings == self.settingsAtStart:
            print("settings are same as at start")
            return
        elif self.app.settings == self.app.settings.defaults:
            print("settings are same as default")
            self.resetSettings()
            miscgraphics.MessageWindow("Settings have been reset to their defaults. "
                                       "Please restart the application to take effects", status='Info')
            return
        else:
            self.app.settings.save(self.app.settings)
            if errors:
                miscgraphics.MessageWindow("There were errors during these parameters saving:\n\n\t" +
                                           "\n\t".join(errors) + "\n\nPlease check input data", status='Error')
            else:
                miscgraphics.MessageWindow("Parameters are successfully saved. Please restart the application to take "
                                           "effects", status='Info')


    def resetSettings(self) -> None:
        """
        Recover settings to their default values

        :return: None
        """

        self.app.settings.persistentStorage.clear()
        self.app.settings.update(copy.deepcopy(self.app.settings.defaults))
        self.updateDisplayingValues()
