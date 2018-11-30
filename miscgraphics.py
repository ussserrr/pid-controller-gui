import multiprocessing.connection
import string

from PyQt5.QtGui import QPainter, QIcon, QPixmap
from PyQt5.QtWidgets import QMessageBox, QAbstractButton, QPushButton, QGroupBox, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import QSize, QTimer

import numpy as np

import pyqtgraph

import remotecontroller


STREAM_PIPE_OVERFLOW_NUM_POINTS_THRESHOLD = 50
STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS = 10000



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



class ValueGroupBox(QGroupBox):
    """

    """

    def __init__(self, label, conn, parent=None):

        super(ValueGroupBox, self).__init__(parent)

        self.setTitle(f"{label.capitalize()} control")

        self.label = label
        self.conn = conn

        self.valLabelTemplate = string.Template("Current $label: <b>{:.3f}</b>").safe_substitute(label=label)
        self.valLabel = QLabel()
        self.refreshVal()
        refreshButton = PicButton("img/refresh.png", "img/refresh_hover.png", "img/refresh_pressed.png")
        refreshButton.clicked.connect(self.refreshVal)
        refreshButton.setIcon(QIcon("img/refresh.png"))
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
        self.valLabel.setText(self.valLabelTemplate.format(self.conn.read(self.label)))


    def writeButtonClicked(self):
        try:
            self.conn.write(self.label, float(self.writeLine.text()))
        except ValueError:
            pass
        self.writeLine.clear()
        self.refreshVal()



class CustomGraphicsLayoutWidget(pyqtgraph.GraphicsLayoutWidget):
    """
    Plots widget with animation support. This class allows to place plots only. To be able to add some other pyqtgraph
    elements you can use pyqtgraph.LayoutWidget as a base instead:

        class CustomLayoutWidget(pyqtgraph.LayoutWidget):

            def __init__(self):
                super(CustomLayoutWidget, self).__init__()

                self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)

                self.procVarGraph = pyqtgraph.PlotWidget(y=np.zeros([self.nPoints]))
                self.procVarGraph.plotItem.setRange(yRange=procVarRange)
                self.addWidget(self.procVarGraph)
                self.nextRow()
                self.averLabel = pyqtgraph.ValueLabel(averageTime=nPoints*interval)
                self.addWidget(self.averLabel)
                self.nextRow()
                self.contOutGraph = pyqtgraph.PlotWidget(y=np.zeros([self.nPoints]))
                self.contOutGraph.plotItem.setRange(yRange=contOutRange)
                self.addWidget(self.contOutGraph)

                self.updateTimer = QTimer()
                self.updateTimer.timeout.connect(self.update_graphs)
                if start:
                    self.start_live_graphs()

            ...

    """

    def __init__(
            self, nPoints: int=200, interval: int=17,
            procVarRange: tuple=(-1.0, 1.0), contOutRange: tuple=(-1.0, 1.0),
            controlPipe: multiprocessing.connection.Connection=None,
            streamPipeRX: multiprocessing.connection.Connection=None,
            theme: str='dark',
    ):
        """
        Graphs' constructor

        :param nPoints: number of points in each graph
        :param interval: time in ms to force the plot refresh
        :param procVarRange: Y-limits of the first plot (process variable)
        :param contOutRange: Y-limits of the second plot (controller output)
        :param controlPipe: multiprocessing.Connection instance to communicate with a stream source
        :param streamPipeRX: multiprocessing.Connection instance from where new points should arrive
        :param theme: string representing visual appearance of the widget ('light' or 'dark')
        """

        # need to set a theme before any other pyqtgraph operations
        if theme != 'dark':
            pyqtgraph.setConfigOption('background', 'w')
            pyqtgraph.setConfigOption('foreground', 'k')

        super(CustomGraphicsLayoutWidget, self).__init__()

        self.nPoints = nPoints
        self.lastPoint = {
            'pv': 0.0,
            'co': 0.0
        }
        self.interval = interval

        # axis is "starting" at the right border (current time) and goes to the past to the left (negative time)
        self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)

        self.controlPipe = controlPipe
        self.overflowCheckTimer = QTimer()
        self.overflowCheckTimer.timeout.connect(self.overflowCheck)

        self.streamPipeRX = streamPipeRX
        self._isRun = False

        # process variable graph
        self.procVarGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Process Variable"},
                                         pen=pyqtgraph.mkPen(color='r'))
        self.procVarGraph.setRange(yRange=procVarRange)
        self.procVarGraph.hideButtons()
        self.procVarGraph.hideAxis('left')
        self.procVarGraph.showGrid(x=True, y=True, alpha=0.2)

        self.nextRow()

        # controller output graph
        self.contOutGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Controller Output", 'bottom': "Time, ms"},
                                         pen=pyqtgraph.mkPen(color='r'))
        self.contOutGraph.setRange(yRange=contOutRange)
        self.contOutGraph.hideButtons()
        self.contOutGraph.hideAxis('left')
        self.contOutGraph.showGrid(x=True, y=True, alpha=0.2)

        # label widget accumulating incoming values and calculating an average from last 'averageTime' seconds
        self.procVarAverLabel = pyqtgraph.ValueLabel(siPrefix=True, suffix='V',
                                                     averageTime=nPoints*interval*0.001)
        self.contOutAverLabel = pyqtgraph.ValueLabel(siPrefix=True, suffix='Parrots',
                                                     averageTime=nPoints*interval*0.001)

        # data receiving and plots redrawing timer
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self._update)

        self.pointsCnt = 0


    @property
    def isRun(self):
        """bool property getter"""
        return self._isRun


    def overflowCheck(self):
        self.controlPipe.send(remotecontroller.InputThreadCommand.MSG_CNT_GET)
        if self.controlPipe.poll(timeout=0.1):
            input_thread_points_cnt = self.controlPipe.recv()
            print(f'sock: {input_thread_points_cnt}, plot: {self.pointsCnt}')
            if input_thread_points_cnt - self.pointsCnt > STREAM_PIPE_OVERFLOW_NUM_POINTS_THRESHOLD:
                print('overflow!')  # TODO: maybe notify the main, maybe use the signal
                # 1. stop incoming stream
                # 2. flush self.pipe (maybe plot this points, maybe drop them)
                # 3. restart the stream
                self.stop()
                self.start()


    def start(self):
        # reset data cause it has changed during the pause time
        self.procVarGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))
        self.contOutGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))
        self.updateTimer.start(self.interval)

        if self.streamPipeRX is not None:
            self.overflowCheckTimer.start(STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS)
            self.controlPipe.send(remotecontroller.InputThreadCommand.STREAM_ACCEPT)

        self._isRun = True


    def stop(self):
        self.updateTimer.stop()

        if self.streamPipeRX is not None:
            self.overflowCheckTimer.stop()
            self.controlPipe.send(remotecontroller.InputThreadCommand.STREAM_REJECT)
            self.controlPipe.send(remotecontroller.InputThreadCommand.MSG_CNT_RST)
            while True:
                if self.streamPipeRX.poll():
                    self.streamPipeRX.recv()
                else:
                    break

        self.pointsCnt = 0
        self._isRun = False


    def toggle(self):
        if self._isRun:
            self.stop()
        else:
            self.start()


    def _update(self):
        if self.streamPipeRX is None:
            self.lastPoint['pv'] = -0.5 + np.random.rand()
            self.lastPoint['co'] = -0.5 + np.random.rand()
            self.pointsCnt += 1
        else:
            try:
                if self.streamPipeRX.poll():
                    point = self.streamPipeRX.recv()
                    self.lastPoint['pv'] = point[0]
                    self.lastPoint['co'] = point[1]
                    self.pointsCnt += 1
            except OSError:
                print("OSError")
                pass

        self.procVarAverLabel.setValue(self.lastPoint['pv'])
        self.contOutAverLabel.setValue(self.lastPoint['co'])

        procVarData = np.roll(self.procVarGraph.curves[0].getData()[1], -1)
        procVarData[-1] = self.lastPoint['pv']
        contOutData = np.roll(self.contOutGraph.curves[0].getData()[1], -1)
        contOutData[-1] = self.lastPoint['co']

        self.procVarGraph.curves[0].setData(self.timeAxes, procVarData)
        self.contOutGraph.curves[0].setData(self.timeAxes, contOutData)



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    from PyQt5.QtWidgets import QWidget, QApplication
    import sys

    app = QApplication(sys.argv)
    window = QWidget()

    graphs = CustomGraphicsLayoutWidget(
        nPoints=200,
        procVarRange=(-2.0, 2.0),
        contOutRange=(-2.0, 2.0),
        interval=17,  # ~60 FPS
        controlPipe=None,
        streamPipeRX=None,
        theme='dark',
    )
    graphs.start()

    layout = QHBoxLayout(window)
    layout.addWidget(graphs)

    window.show()
    sys.exit(app.exec_())
