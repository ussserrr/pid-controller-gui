from PyQt5.QtGui import QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import QMessageBox, QHBoxLayout, QWidget, QAbstractButton, QSizePolicy, QApplication, QLabel, QGridLayout
from PyQt5.QtCore import QSize, QTimer, QThread, QObject, QEvent, QEventLoop, QCoreApplication

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas,\
                                               NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import rcParams
import matplotlib.pyplot as plt
plt.style.use('dark_background')

import matplotlib.animation as animation
import numpy as np
# import multiprocessing as mp



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


class CustomFigureCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=3, dpi=100, xlabel='', ylabel='',
                 ymin=0, ymax=0, auto_ylim=True, Xarray=[], Yarray=[]):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        fig.patch.set_alpha(0)
        rcParams.update({"font.size": 8})

        self.compute_initial_figure()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.axes.grid(color='gray', linestyle=':')
        self.axes.set_ylabel(ylabel)
        self.axes.set_xlabel(xlabel)
        self.axes.xaxis.set_label_position('top')
        self.axes.yaxis.set_label_position('right')

        self.canvas = FigureCanvas(fig)
        self.graphToolbar = NavigationToolbar(self.canvas, self)

    def compute_initial_figure(self):
        pass

    def getGraphToolbar(self):
        return self.graphToolbar


N = 100
class Graph(CustomFigureCanvas):

    # """
    # Graph class for embedding in PyQt5 apps.
    #
    # Usage example:
    #
    #     if __name__ == '__main__':    #
    #         app = QApplication(sys.argv)
    #         mygraph = Graph()
    #         window = QWidget()
    #         layout = QHBoxLayout(window)
    #         layout.addWidget(mygraph)
    #         window.show()
    #         sys.exit(app.exec_())
    #
    # """

    def __init__(self, *args, **kwargs):
        CustomFigureCanvas.__init__(self, *args, **kwargs)
        timer = QTimer(self)
        timer.timeout.connect(self.update_figure)
        timer.start(75)

    def compute_initial_figure(self):
        self.x = np.arange(0, N, 1)
        self.y = 4.5 + np.random.rand(N)
        self.line = self.axes.plot(self.x, self.y)[0]
        self.axes.set_ylim([0.0, 10.0])

    def update_figure(self):
        self.y = np.append(self.y[1:], 4.5+np.random.rand())
        self.line.set_ydata(self.y)
        self.draw()


    # def __init__(self, parent=None, width=5, height=3, dpi=100, xlabel='', ylabel='',
    #              ymin=0, ymax=0, auto_ylim=True, Xarray=[], Yarray=[]):
    #
    #     fig = Figure(figsize=(width, height), dpi=dpi)
    #     axes = fig.add_subplot(111)
    #
    #     FigureCanvas.__init__(self, fig)
    #     # FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
    #     # FigureCanvas.updateGeometry(self)
    #
    #     fig.patch.set_alpha(0)
    #     rcParams.update({"font.size": 8})
    #     axes.grid(color='gray', linestyle=':')
    #     axes.set_ylabel(ylabel)
    #     axes.set_xlabel(xlabel)
    #     axes.xaxis.set_label_position('top')
    #     axes.yaxis.set_label_position('right')
    #     # if not auto_ylim:
    #     axes.set_ylim([0.0, 1.0])
    #
    #     self.line, = axes.plot(range(100), np.random.random(100))
    #     self.lineTuple = (self.line,)
    #
    #     # axes.plot(Xarray, Yarray)
    #
    #     self.canvas = FigureCanvas(fig)
    #     self.graphToolbar = NavigationToolbar(self.canvas, self)


class TestWindow(QWidget):
    def __init__(self, parent=None):
        super(TestWindow, self).__init__(parent)
        self.setWindowTitle("Test")

        self.label = QLabel("*** TEST TEST TEST ***")

        grid = QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.label)
