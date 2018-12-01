import string

from PyQt5.QtGui import QPainter, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QMessageBox, QAbstractButton, QPushButton, QGroupBox, QLabel,\
                            QLineEdit
from PyQt5.QtCore import QSize

# local imports
import remotecontroller



class PicButton(QAbstractButton):
    """
    Custom button with 3 different looks: for normal, when mouse is over it and pressed states

    Usage example:

        import sys
        from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout

        app = QApplication(sys.argv)
        button = PicButton("img/refresh.png", "img/refresh_hover.png", "img/refresh_pressed.png")
        window = QWidget()
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


    def paintEvent(self, event):
        if self.isDown():
            pix = self.pixmap_pressed
        elif self.underMouse():
            pix = self.pixmap_hover
        else:
            pix = self.pixmap

        QPainter(self).drawPixmap(event.rect(), pix)


    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def sizeHint(self):
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

    def __init__(self, label: str, controller: remotecontroller.RemoteController, parent=None):
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
        self.valLabelTemplate = string.Template("Current $label: <b>{:.3f}</b>").safe_substitute(label=label)
        self.valLabel = QLabel()
        self.refreshVal()

        refreshButton = PicButton("img/refresh.png", "img/refresh_hover.png", "img/refresh_pressed.png")
        refreshButton.clicked.connect(self.refreshVal)
        # refreshButton.setIcon(QIcon("img/refresh.png"))

        self.writeLine = QLineEdit()
        self.writeLine.setPlaceholderText(f"Enter new '{label}'")
        writeButton = QPushButton('Send', self)
        writeButton.clicked.connect(self.writeButtonClicked)

        hBox1 = QHBoxLayout()
        hBox1.addWidget(self.valLabel)
        hBox1.addStretch(1)
        hBox1.addWidget(refreshButton)

        hBox2 = QHBoxLayout()
        hBox2.addWidget(self.writeLine)
        hBox2.addWidget(writeButton)

        vBox1 = QVBoxLayout()
        vBox1.addLayout(hBox1)
        vBox1.addLayout(hBox2)

        self.setLayout(vBox1)


    def refreshVal(self):
        """
        Read a value from the RemoteController

        :return: None
        """

        self.valLabel.setText(self.valLabelTemplate.format(self.controller.read(self.label)))


    def writeButtonClicked(self):
        """
        Send a new value to the RemoteController

        :return: None
        """

        try:
            self.controller.write(self.label, float(self.writeLine.text()))
        except ValueError:  # user enters not valid number or NaN
            pass
        self.writeLine.clear()
        self.refreshVal()  # read a value back to make sure writing was successful (not really necessary to perform)



if __name__ == '__main__':
    pass
