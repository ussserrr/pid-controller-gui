from PyQt5.QtGui import QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import QMessageBox, QHBoxLayout, QWidget, QAbstractButton
from PyQt5.QtCore import QSize

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas,\
                                               NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import rcParams



class PicButton(QAbstractButton):

    """
    Custom button with 3 different pics when button is alone,
    when hovered by cursor and when pressed.

    Usage example:

        if __name__ == '__main__':
            import sys
            from PyQt5.QtWidgets import QApplication

            app = QApplication(sys.argv)
            button = PicButton(QPixmap("alone.png"),
                               QPixmap("hovered.png"),
                               QPixmap("pressed.png"))
            window = QWidget()
            layout = QHBoxLayout(window)
            layout.addWidget(button)
            window.show()
            sys.exit(app.exec_())

    """

    def __init__(self, pixmap, pixmap_hover, pixmap_pressed, parent=None):
        super(PicButton, self).__init__(parent)

        self.pixmap = pixmap
        self.pixmap_hover = pixmap_hover
        self.pixmap_pressed = pixmap_pressed

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
    Standalone window representing Info, Warning or Error with corresponding
    system icon and user text

    Usage example:

        if __name__ == '__main__':
            import sys
            from PyQt5.QtWidgets import QApplication

            app = QApplication(sys.argv)
            MessageWindow(text="Hello", type='Info')

    """

    def __init__(self, parent=None, text='', type='Warning'):
        super(MessageWindow, self).__init__(parent)
        self.setWindowTitle(type)
        self.setWindowIcon(QIcon('img/error.png'))

        if type == 'Info':
            self.setIcon(QMessageBox.Information)
        elif type == 'Warning':
            self.setIcon(QMessageBox.Warning)
        elif type == 'Error':
            self.setIcon(QMessageBox.Critical)

        self.setText(text)
        self.setStandardButtons(QMessageBox.Ok)

        self.exec_()



class Graph(FigureCanvas):

    """
    Graph class for embedding in PyQt5 apps.

    Usage example:

        if __name__ == '__main__':
            import sys

            app = QApplication(sys.argv)
            mygraph = Graph()
            window = QWidget()
            layout = QHBoxLayout(window)
            layout.addWidget(mygraph)
            window.show()
            sys.exit(app.exec_())

    """

    def __init__(self, parent=None, width=5, height=3, dpi=100, xlabel='', ylabel='',
                 ymin=0, ymax=0, auto_ylim=True, Xarray=[], Yarray=[]):

        fig = Figure(figsize=(width, height), dpi=dpi)
        axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        # FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        # FigureCanvas.updateGeometry(self)

        fig.patch.set_alpha(0)
        rcParams.update({"font.size": 8})
        axes.grid(color='gray', linestyle=':')
        axes.set_ylabel(ylabel)
        axes.set_xlabel(xlabel)
        axes.xaxis.set_label_position('top')
        axes.yaxis.set_label_position('right')
        if not auto_ylim: axes.set_ylim([ymin, ymax])

        axes.plot(Xarray, Yarray)

        self.canvas = FigureCanvas(fig)
        self.graphToolbar = NavigationToolbar(self.canvas, self)


    def getGraphToolbar(self):
        return self.graphToolbar
