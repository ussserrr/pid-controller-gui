"""
about.py - holds packages information, credits and so on


ABOUT_TEXT
    HTML-formatted 'about' text

SYS_TEXT
    HTML-formatted 'system' text


AboutWindow
    QTabWidget window
"""

import platform
import sys

from PyQt5.Qt import PYQT_VERSION_STR
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QLabel, QTextBrowser, QPushButton, QStyle
from PyQt5.QtGui import QIcon, QPixmap



LOGO_SIZE = 96



ABOUT_TEXT = """<!DOCTYPE html>
<html>
<body align="center">

<h3>PID controller GUI</h3>

<p>(C) Andrey Chufyrev</p>

<p>2016-2018</p>

<p>Repository: <a href="https://github.com/ussserrr/maglev-client">https://github.com/ussserrr/maglev-client</a></p>

</body>
</html>
"""



SYS_TEXT = f"""<!DOCTYPE html>
<html>
<body>

<h2>Python</h2>
<ul>
  <li>{sys.version}</li>
</ul>

<h2>Platform</h2>
<ul>
  <li>{platform.platform(aliased=True)}</li>
</ul>

<h2>PyQt</h2>
<ul>
  <li>{PYQT_VERSION_STR}</li>
</ul>

<h2>PyQtGraph</h2>
<ul>
  <li><a href="https://github.com/pyqtgraph/pyqtgraph">https://github.com/pyqtgraph/pyqtgraph</a></li>
</ul>

<h2>QDarkStylesheet</h2>
<ul>
  <li><a href="https://github.com/ColinDuquesnoy/QDarkStyleSheet">
  https://github.com/ColinDuquesnoy/QDarkStyleSheet</a></li>
</ul>

<h2>Icons</h2>
<ul>
  <li>All icons belongs to their respective authors from <a href="https://www.flaticon.com">FlatIcon.com</a></li>
</ul>

</body>
</html>
"""



class AboutWindow(QTabWidget):
    """
    Some service information, credits using html documents
    """

    def __init__(self, parent=None):
        """
        AboutWindow constructor

        :param parent: [optional] parent class
        """

        super(AboutWindow, self).__init__(parent)

        self.setWindowTitle("Info & About")
        self.setWindowIcon(QIcon('img/info.png'))

        self.aboutTab = QWidget()
        self.sysTab = QWidget()

        self.addTab(self.aboutTab, 'About')
        self.addTab(self.sysTab, 'System')

        self.initAboutTabUI()
        self.initSysTabUI()


    def initAboutTabUI(self) -> None:
        """
        Initialize 'About' tab

        :return: None
        """

        layout = QVBoxLayout()
        self.aboutTab.setLayout(layout)

        # prepare logo view: create pixmap, scale it using nicer method
        iconPixmap = QPixmap('img/icon.png').scaledToWidth(LOGO_SIZE, Qt.SmoothTransformation)
        iconLabel = QLabel()  # QLabel is used to store the pixmap
        iconLabel.setPixmap(iconPixmap)
        iconLabel.setAlignment(Qt.AlignCenter)

        aboutTextBrowser = QTextBrowser()  # read-only text holder with rich text support
        aboutTextBrowser.setHtml(ABOUT_TEXT)
        aboutTextBrowser.setOpenExternalLinks(True)

        layout.addSpacing(40)
        layout.addWidget(iconLabel, Qt.AlignCenter)
        layout.addSpacing(40)
        layout.addWidget(aboutTextBrowser)


    def initSysTabUI(self) -> None:
        """
        Initialize 'System' tab

        :return: None
        """

        layout = QVBoxLayout()
        self.sysTab.setLayout(layout)

        sysTextBrowser = QTextBrowser()
        sysTextBrowser.setHtml(SYS_TEXT)
        sysTextBrowser.setOpenExternalLinks(True)

        aboutQtButton = QPushButton(QIcon(self.style().standardIcon(QStyle.SP_TitleBarMenuButton)), 'About QT')
        aboutQtButton.clicked.connect(QApplication.instance().aboutQt)

        layout.addWidget(sysTextBrowser)
        layout.addWidget(aboutQtButton)



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    app = QApplication(sys.argv)

    aboutWindow = AboutWindow()
    aboutWindow.show()

    sys.exit(app.exec_())
