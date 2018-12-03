"""
Docstring
"""

import random
import string

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QPainter, QIcon, QPixmap, QDoubleValidator
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QMessageBox, QAbstractButton, QPushButton, QGroupBox, QLabel,\
                            QLineEdit

# local imports
import remotecontroller



class PicButton(QAbstractButton):
    """
    Custom button with 3 different looks: for normal, when mouse is over it and pressed states

    Usage example:

        import sys
        from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout

        app = QApplication(sys.argv)
        window = QWidget()
        button = PicButton("img/refresh.png", "img/refresh_hover.png", "img/refresh_pressed.png")
        layout = QHBoxLayout(window)
        layout.addWidget(button)
        window.show()
        sys.exit(app.exec_())

    """

    def __init__(self, img_normal: str, img_hover: str, img_pressed: str, parent=None):
        """
        PicButton constructor

        :param img_normal: path to an image that should represent a normal state of the button
        :param img_hover: path to an image that should represent a state of the button when the mouse cursor is hovering
        over it
        :param img_pressed: path to an image that should represent a pressed state of the button
        :param parent: [optional] parent class
        """

        super(PicButton, self).__init__(parent)

        self.pixmap = QPixmap(img_normal)
        self.pixmap_hover = QPixmap(img_hover)
        self.pixmap_pressed = QPixmap(img_pressed)

        self.pressed.connect(self.update)
        self.released.connect(self.update)


    def paintEvent(self, event) -> None:
        if self.isDown():
            pix = self.pixmap_pressed
        elif self.underMouse():
            pix = self.pixmap_hover
        else:
            pix = self.pixmap

        QPainter(self).drawPixmap(event.rect(), pix)


    def enterEvent(self, event) -> None:
        self.update()

    def leaveEvent(self, event) -> None:
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(24, 24)



class MessageWindow(QMessageBox):

    """
    Standalone window representing Info, Warning or Error with corresponding system icon and user text

    Usage example:

        if __name__ == '__main__':
            import sys
            from PyQt5.QtWidgets import QApplication

            app = QApplication(sys.argv)
            MessageWindow("Hello", status='Info')

    """

    def __init__(self, text: str, status: str='Warning', parent=None):
        """
        MessageWindow constructor

        :param text: string to show
        :param status: string representing message urgency ('Info', 'Warning' or 'Error')
        :param parent: [optional] parent class
        """

        super(MessageWindow, self).__init__(parent)

        self.setWindowTitle(status)
        self.setWindowIcon(QIcon('img/error.png'))

        if status == 'Info':
            self.setIcon(QMessageBox.Information)
        elif status == 'Warning':
            self.setIcon(QMessageBox.Warning)
        elif status == 'Error':
            self.setIcon(QMessageBox.Critical)

        self.setText(text)
        self.setStandardButtons(QMessageBox.Ok)

        self.exec_()



class ValueGroupBox(QGroupBox):
    """
    QGroupBox widget centered around a single numerical variable. It combines a QLabel to show the current value, a
    refresh PicButton to explicitly update it and a QLineEdit with an associated QPushButton to set a new value.
    """

    def __init__(self, label: str, float_fmt: str= '{:.3f}', controller: remotecontroller.RemoteController=None, parent=None):
        """
        ValueGroupBox constructor

        :param label: name of the GroupBox
        :param controller: RemoteController instance to connect to
        :param parent: [optional] parent class
        """

        super(ValueGroupBox, self).__init__(parent)

        self.setTitle(f"{label.capitalize()} control")

        self.label = label
        self.controller = controller

        # prepare a template string using another template string :)
        self.valLabelTemplate = string.Template(f"Current $label: <b>{float_fmt}</b>").safe_substitute(label=label)
        self.valLabel = QLabel()
        self.refreshVal()

        refreshButton = PicButton('img/refresh.png', 'img/refresh_hover.png', 'img/refresh_pressed.png')
        refreshButton.clicked.connect(self.refreshVal)

        self.writeLine = QLineEdit()
        self.writeLine.setPlaceholderText(f"Enter new '{label}'")
        self.writeLine.setValidator(QDoubleValidator())  # we can set a Locale() to correctly process floats
        self.writeLine.setToolTip("Float value")
        writeButton = QPushButton('Send', self)
        writeButton.clicked.connect(self.writeButtonClicked)

        hBox1 = QHBoxLayout()
        hBox1.addWidget(self.valLabel)
        hBox1.addStretch()  # need to not distort the button when resizing
        hBox1.addSpacing(25)
        hBox1.addWidget(refreshButton)

        hBox2 = QHBoxLayout()
        hBox2.addWidget(self.writeLine)
        hBox2.addWidget(writeButton)

        vBox1 = QVBoxLayout()
        vBox1.addLayout(hBox1)
        vBox1.addLayout(hBox2)

        self.setLayout(vBox1)


    def refreshVal(self) -> None:
        """
        Read a value from the RemoteController

        :return: None
        """

        if self.controller is not None:
            self.valLabel.setText(self.valLabelTemplate.format(self.controller.read(self.label)))
        else:
            self.valLabel.setText(self.valLabelTemplate.format(random.random()))


    def writeButtonClicked(self) -> None:
        """
        Send a new value to the RemoteController

        :return: None
        """

        try:
            if self.controller is not None:
                self.controller.write(self.label, float(self.writeLine.text()))
        except ValueError:  # user enters not valid number or NaN
            pass
        self.writeLine.clear()
        # read a value back to make sure that writing was successful (not really necessary to perform)
        self.refreshVal()



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    import sys
    from PyQt5.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)
    window = QWidget()

    button = PicButton("img/refresh.png", "img/refresh_hover.png", "img/refresh_pressed.png")
    button.clicked.connect(lambda: print("PicButton has been clicked"))

    valueBox = ValueGroupBox("My value")

    invokeMessageWindow = QPushButton("Message window")
    invokeMessageWindow.clicked.connect(lambda: MessageWindow("I am MessageWindow", status='Info'))

    layout = QHBoxLayout(window)
    layout.addWidget(button)
    layout.addWidget(valueBox)
    layout.addWidget(invokeMessageWindow)

    window.show()
    app.aboutQt()

    sys.exit(app.exec_())
