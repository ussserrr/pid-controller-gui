import copy
import json
import ipaddress

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget, QRadioButton, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QSpinBox, QButtonGroup
from PyQt5.QtGui import QIcon

from miscgraphics import MessageWindow




class Settings(dict):

    def __init__(self, defaults=''):

        super(Settings, self).__init__()

        with open(defaults, mode='r') as defaultSettingsJSONFile:
            self.defaults = json.load(defaultSettingsJSONFile)

        self.persistentStorage = QSettings()
        # self.persistentStorage.clear()
        self._retrieve()


    def _retrieve(self):
        self.persistentStorage.beginGroup('app')

        if not self.persistentStorage.contains("settings"):
            print("No settings, clear all, use default...")
            print(len(self.persistentStorage.allKeys()))
            self.persistentStorage.endGroup()
            self.persistentStorage.clear()

            # self.save(self.defaults)
            self.update(copy.deepcopy(self.defaults))  # we assume that 'defaults' will not change but for a confidence we make a copy
            # return copy.deepcopy(self.defaultSettings)
        else:
            print("Restore from NV-storage")
            print(len(self.persistentStorage.allKeys()))
            self.update(self.persistentStorage.value("settings", type=dict))
            self.persistentStorage.endGroup()
            # return self.persistentStorage.value("settings", type=dict)


    def save(self, settings):
        print("Saving settings...")
        self.persistentStorage.beginGroup('app')
        self.persistentStorage.setValue('settings', copy.deepcopy(settings))
        self.persistentStorage.endGroup()


    def __deepcopy__(self, memodict={}):
        return copy.deepcopy(dict(self))




class SettingsWindow(QWidget):

    def __init__(self, app, parent=None):

        super(SettingsWindow, self).__init__(parent)

        self.app = app

        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon('img/settings.png'))

        self.settingsAtStart = copy.deepcopy(app.settings)

        self.wereReset = False
        self.isFirstShow = True

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
        networkVBox = QVBoxLayout()
        networkGroupBox.setLayout(networkVBox)

        networkHBox1 = QHBoxLayout()
        self.ipLineEdit = QLineEdit()
        self.portLineEdit = QLineEdit()
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
        # self.connCheckIntervalSpinBox.setValue(self.app.settings['network']['checkInterval'])
        networkHBox2.addWidget(QLabel("Checks interval:"))
        networkHBox2.addWidget(self.connCheckIntervalSpinBox)

        networkVBox.addLayout(networkHBox1)
        networkVBox.addLayout(networkHBox2)



        themeGroupBox = QGroupBox('Theme')
        themeHBox = QHBoxLayout()
        themeGroupBox.setLayout(themeHBox)

        self.themeLightRadioButton = QRadioButton('Light')
        self.themeDarkRadioButton = QRadioButton('Dark')
        themeButtonGroup = QButtonGroup(themeGroupBox)
        themeButtonGroup.addButton(self.themeLightRadioButton)
        themeButtonGroup.addButton(self.themeDarkRadioButton)

        # if self.app.settings['appearance']['theme'] == 'light':
        #     self.themeLightRadioButton.setChecked(True)
        # else:
        #     self.themeDarkRadioButton.setChecked(True)

        themeHBox.addWidget(self.themeLightRadioButton)
        themeHBox.addWidget(self.themeDarkRadioButton)


        graphsGroupBox = QGroupBox("Graphics")
        graphsVBox = QVBoxLayout()
        graphsGroupBox.setLayout(graphsVBox)

        graphsHBox1 = QHBoxLayout()
        self.graphsUpdateIntervalSpinBox = QSpinBox()
        self.graphsUpdateIntervalSpinBox.setSuffix(" ms")
        self.graphsUpdateIntervalSpinBox.setMinimum(1)
        self.graphsUpdateIntervalSpinBox.setMaximum(1e9)
        self.graphsUpdateIntervalSpinBox.setSingleStep(10)
        # self.graphsUpdateIntervalSpinBox.setValue(self.app.settings['graphs']['updateInterval'])
        graphsHBox1.addWidget(QLabel("Update interval:"))
        graphsHBox1.addWidget(self.graphsUpdateIntervalSpinBox)

        graphsHBox2 = QHBoxLayout()
        self.graphsNumberOfPointsSpinBox = QSpinBox()
        self.graphsNumberOfPointsSpinBox.setMinimum(3)
        self.graphsNumberOfPointsSpinBox.setMaximum(1e5)
        self.graphsNumberOfPointsSpinBox.setSingleStep(50)
        # self.graphsNumberOfPointsSpinBox.setValue(self.app.settings['graphs']['numberOfPoints'])
        graphsHBox2.addWidget(QLabel("Number of points:"))
        graphsHBox2.addWidget(self.graphsNumberOfPointsSpinBox)

        graphsVBox.addLayout(graphsHBox1)
        graphsVBox.addLayout(graphsHBox2)


        resetSettingsButton = QPushButton("Reset to defaults")
        resetSettingsButton.clicked.connect(self.resetSettings)


        self.updateDisplayingValues()


        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(themeGroupBox)
        grid.addWidget(networkGroupBox)
        grid.addWidget(graphsGroupBox)
        grid.addWidget(resetSettingsButton)


    def updateDisplayingValues(self):
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
        self.updateDisplayingValues()
        super(SettingsWindow, self).show()


    def closeEvent(self, event):
        if not self.wereReset:
            self.saveSettings()
        else:
            if self.isFirstShow:
                self.isFirstShow = False
            else:
                MessageWindow(text="Settings have been reset earlier, please restart the application first to edit them")


    def saveSettings(self):

        errors = []

        try:
            # TODO: switch to QLineEdit' built-in method
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


        if self.app.settings == self.settingsAtStart:  # MB HERE
            print("settings same as at start")
            return
        else:
            self.app.settings.save(self.app.settings)  # MB HERE
            if errors:
                MessageWindow(text="There were errors during these parameters saving:\n\n\t" + "\n\t".join(errors) +
                               "\n\nPlease check input data",
                              type='Error')
            else:
                MessageWindow(text="Parameters are successfully saved. Please restart the application to take effects", type='Info')


    def resetSettings(self):
        self.app.settings.persistentStorage.clear()
        self.app.settings.update(self.app.settings.defaults)
        # self.app.settings.save(self.app.settings.defaults)
        MessageWindow(text="Settings have been reset to their defaults. Please restart the application to take effects", type='Info')
        self.wereReset = True
        self.close()