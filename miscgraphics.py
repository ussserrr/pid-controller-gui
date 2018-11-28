import string

from PyQt5.QtGui import QPainter, QIcon, QPixmap
from PyQt5.QtWidgets import QMessageBox, QAbstractButton, QPushButton, QGroupBox, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import QSize, QTimer

import numpy as np

import pyqtgraph



class PicButton(QAbstractButton):

    """
    Custom button with 3 different pics when button is alone,
    when hovered by cursor and when pressed.

    Usage example:

        # button_test.py

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

    def __init__(self, img_normal, img_hover, img_pressed, parent=None):
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
    This class allows to place plots only. To be able to add some other pyqtgraph elements you can use
    pyqtgraph.LayoutWidget as a base instead:

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

    def __init__(self, nPoints=200, procVarRange=(0.0, 0.0), contOutRange=(0.0, 0.0), interval=19,
                 control_pipe=None, stream_pipe_rx=None, theme='dark', start=False):

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

        self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)

        self.control_pipe = control_pipe
        self.overflowCheckTimer = QTimer()
        self.overflowCheckTimer.timeout.connect(self.overflowCheck)

        self.stream_pipe_rx = stream_pipe_rx
        self.isRun = False

        self.procVarGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Process Variable"},
                                         pen=pyqtgraph.mkPen(color='r'))
        if procVarRange != (0, 0):
            self.procVarGraph.setRange(yRange=procVarRange)
        self.procVarGraph.hideButtons()
        self.procVarGraph.hideAxis('left')
        self.procVarGraph.showGrid(x=True, y=True, alpha=0.2)

        self.nextRow()

        self.contOutGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Controller Output", 'bottom': "Time, ms"},
                                         pen=pyqtgraph.mkPen(color='r'))
        if contOutRange != (0, 0):
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

        self.points_cnt = 0


    def overflowCheck(self):
        self.control_pipe.send('get')
        if self.control_pipe.poll(timeout=0.1):
            input_thread_points_cnt = self.control_pipe.recv()
            print(f'sock: {input_thread_points_cnt}, plot: {self.points_cnt}')
            if input_thread_points_cnt - self.points_cnt >= input_thread_points_cnt * 0.05:
                print('overflow!')  # TODO: maybe notify the main, maybe use the signal
                # 1. stop incoming stream
                # 2. flush self.pipe (maybe plot this points, maybe drop them)
                # 3. restart the stream
                self.pause_live_graphs()
                self.start_live_graphs()


    def start_live_graphs(self):
        # reset data cause it has changed during the pause time
        self.procVarGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))
        self.contOutGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))
        self.updateTimer.start(self.interval)

        if self.stream_pipe_rx is not None:
            self.overflowCheckTimer.start(10000)
            self.control_pipe.send('run')

        self.isRun = True


    def pause_live_graphs(self):
        self.updateTimer.stop()

        if self.stream_pipe_rx is not None:
            self.overflowCheckTimer.stop()
            self.control_pipe.send('rst')
            while True:
                if self.stream_pipe_rx.poll():
                    self.stream_pipe_rx.recv()
                else:
                    break

        self.points_cnt = 0
        self.isRun = False


    def toggle_live_graphs(self):
        if self.isRun:
            self.pause_live_graphs()
        else:
            self.start_live_graphs()


    def update_graphs(self):
        if self.stream_pipe_rx is None:
            self.lastPoint['pv'] = -0.5 + np.random.rand()
            self.lastPoint['co'] = -0.5 + np.random.rand()
            self.points_cnt += 1
        else:
            try:
                if self.stream_pipe_rx.poll():
                    point = self.stream_pipe_rx.recv()
                    self.lastPoint['pv'] = point[0]
                    self.lastPoint['co'] = point[1]
                    self.points_cnt += 1
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
