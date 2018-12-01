from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLayout, QVBoxLayout, QTabWidget, QSizePolicy, QLabel
from PyQt5.QtGui import QIcon


aboutInfo = "la"


class AboutWindow(QTabWidget):
    """

    """

    def __init__(self, app, parent=None):
        """

        :param app:
        :param parent:
        """

        super(AboutWindow, self).__init__(parent)

        self.app = app

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
        sysTabText = QLabel("IP-address of MCU: {}\nUDP-port: {}".format(self.app.settings['network']['ip'], self.app.settings['network']['port']))
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
