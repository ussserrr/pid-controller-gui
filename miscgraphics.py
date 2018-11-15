from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtWidgets import QMessageBox, QAbstractButton
from PyQt5.QtCore import QSize, QTimer

import numpy as np

import pyqtgraph




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



# class CustomLayoutWidget(pyqtgraph.LayoutWidget):
#     """
#
#     """
#
#     def __init__(self, nPoints=200, procVarRange=(0.0, 1.0), contOutRange=(0.0, 1.0), interval=17, start=False):
#         super(CustomLayoutWidget, self).__init__()
#
#         self.nPoints = nPoints
#         self.interval = interval
#
#         self.run = False
#
#         self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)
#
#         self.procVarGraph = pyqtgraph.PlotWidget(y=np.zeros([self.nPoints]), labels={'right': "Process Variable"})
#         self.procVarGraph.plotItem.setRange(yRange=procVarRange)
#         self.addWidget(self.procVarGraph)
#         self.nextRow()
#         self.averLabel = pyqtgraph.ValueLabel(averageTime=nPoints*interval)
#         self.addWidget(self.averLabel)
#         self.nextRow()
#         self.contOutGraph = pyqtgraph.PlotWidget(y=np.zeros([self.nPoints]), labels={'right': "Controller Output", 'bottom': "Time, ms"})
#         self.contOutGraph.plotItem.setRange(yRange=contOutRange)
#         self.addWidget(self.contOutGraph)
#
#         self.updateTimer = QTimer()
#         self.updateTimer.timeout.connect(self.update_graphs)
#         if start:
#             self.start_live_graphs()
#
#     def start_live_graphs(self):
#         self.run = True
#         self.updateTimer.start(self.interval)
#
#     def pause_live_graphs(self):
#         self.run = False
#         self.updateTimer.stop()
#
#     def toggle_live_graphs(self):
#         if self.run:
#             self.pause_live_graphs()
#         else:
#             self.start_live_graphs()
#
#     def update_graphs(self):
#         self.averLabel.setValue(4.5 + np.random.rand())
#         procVarData = np.roll(self.procVarGraph.plotItem.curves[0].getData()[1], -1)
#         procVarData[-1] = 4.5 + np.random.rand()
#         contOutData = np.roll(self.contOutGraph.plotItem.curves[0].getData()[1], -1)
#         contOutData[-1] = 4.5 + np.random.rand()
#         self.procVarGraph.plotItem.curves[0].setData(self.timeAxes, procVarData)
#         self.contOutGraph.plotItem.curves[0].setData(self.timeAxes, contOutData)



class CustomGraphicsLayoutWidget(pyqtgraph.GraphicsLayoutWidget):
    """

    """

    def __init__(self, nPoints=200, procVarRange=(0,0), contOutRange=(0,0), interval=17, theme='dark', start=False):

        if theme != 'dark':
            pyqtgraph.setConfigOption('background', 'w')
            pyqtgraph.setConfigOption('foreground', 'k')

        super(CustomGraphicsLayoutWidget, self).__init__()

        self.nPoints = nPoints
        self.interval = interval
        self.run = False
        self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)

        self.procVarGraph = self.addPlot(y=np.zeros([self.nPoints]), labels={'right': "Process Variable"}, pen=pyqtgraph.mkPen(color='r'))
        if procVarRange != (0,0):
            self.procVarGraph.setRange(yRange=procVarRange)
        self.procVarGraph.hideButtons()
        self.procVarGraph.hideAxis('left')
        self.procVarGraph.showGrid(x=True, y=True, alpha=0.2)

        self.nextRow()

        self.contOutGraph = self.addPlot(y=np.zeros([self.nPoints]), labels={'right': "Controller Output", 'bottom': "Time, ms"}, pen=pyqtgraph.mkPen(color='r'))
        if contOutRange != (0,0):
            self.contOutGraph.setRange(yRange=contOutRange)
        self.contOutGraph.hideButtons()
        self.contOutGraph.hideAxis('left')
        self.contOutGraph.showGrid(x=True, y=True, alpha=0.2)

        self.procVarAverLabel = pyqtgraph.ValueLabel(siPrefix=True, suffix='V', averageTime=nPoints*interval)
        self.contOutAverLabel = pyqtgraph.ValueLabel(siPrefix=True, suffix='Parrots', averageTime=nPoints*interval)

        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.update_graphs)
        if start:
            self.start_live_graphs()

    def start_live_graphs(self):
        self.run = True
        self.updateTimer.start(self.interval)

    def pause_live_graphs(self):
        self.run = False
        self.updateTimer.stop()

    def toggle_live_graphs(self):
        if self.run:
            self.pause_live_graphs()
        else:
            self.start_live_graphs()

    def update_graphs(self):
        self.procVarAverLabel.setValue(4.5 + np.random.rand())
        self.contOutAverLabel.setValue(4.5 + np.random.rand())

        procVarData = np.roll(self.procVarGraph.curves[0].getData()[1], -1)
        procVarData[-1] = 4.5 + np.random.rand()
        contOutData = np.roll(self.contOutGraph.curves[0].getData()[1], -1)
        contOutData[-1] = 4.5 + np.random.rand()
        self.procVarGraph.curves[0].setData(self.timeAxes, procVarData)
        self.contOutGraph.curves[0].setData(self.timeAxes, contOutData)
