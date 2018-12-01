import multiprocessing.connection

import numpy as np

import pyqtgraph

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QVBoxLayout

# local imports
import remotecontroller



STREAM_PIPE_OVERFLOW_NUM_POINTS_THRESHOLD = 50
STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS = 10000
STREAM_PIPE_OVERFLOW_WARNING_SIGN_DURATION = 5000



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

        self.procVarRange = procVarRange
        self.contOutRange = contOutRange

        # axis is "starting" at the right border (current time) and goes to the past to the left (negative time)
        self.timeAxes = np.linspace(-nPoints*interval, 0, nPoints)

        if controlPipe is not None and streamPipeRX is not None:
            self._isOfflineMode = False

            self.controlPipe = controlPipe

            self.overflowCheckTimer = QTimer()
            self.overflowCheckTimer.timeout.connect(self._overflowCheck)

            self.streamPipeRX = streamPipeRX
        else:
            self._isOfflineMode = True

        self._isRun = False

        # process variable graph
        self.procVarGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Process Variable"}, pen='r')
        self.procVarGraph.setRange(yRange=procVarRange)
        self.procVarGraph.hideButtons()
        self.procVarGraph.hideAxis('left')
        self.procVarGraph.showGrid(x=True, y=True, alpha=0.2)

        self.nextRow()

        # controller output graph
        self.contOutGraph = self.addPlot(y=np.zeros([self.nPoints]),
                                         labels={'right': "Controller Output", 'bottom': "Time, ms"}, pen='r')
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

        self._warningSign = None
        self.warningSignRemoveTimer = QTimer()
        self.warningSignRemoveTimer.setSingleShot(True)
        self.warningSignRemoveTimer.setInterval(STREAM_PIPE_OVERFLOW_WARNING_SIGN_DURATION)
        self.warningSignRemoveTimer.timeout.connect(self._removeWarningSign)


    @property
    def isRun(self) -> bool:
        """bool property getter"""
        return self._isRun


    def _addWarningSign(self):
        self._warningSign = self.procVarGraph.plot(y=[self.procVarRange[1]*0.75], x=[-self.nPoints*self.interval*0.95],
                                                   symbol='o', symbolSize=24, symbolPen='r', symbolBrush='r')

    def _removeWarningSign(self):
        self.procVarGraph.removeItem(self._warningSign)


    def _overflowCheck(self):
        """
        Procedure to check the stream pipe overflow. When a rate of incoming stream socket packets is faster than an
        update time period of this graphs (i.e. pipe' readings) an internal buffer of the pipe entity will grow. We
        responsible for the detection of such situations because quite soon after this the entire connection tends to
        be an unresponsive

        :return: None
        """

        # request to read a points (messages) counter
        self.controlPipe.send(remotecontroller.InputThreadCommand.MSG_CNT_GET)
        if self.controlPipe.poll(timeout=0.1):  # wait for it ...
            input_thread_points_cnt = self.controlPipe.recv()  # ... and read it

            print(f'sock: {input_thread_points_cnt}, plot: {self.pointsCnt}')

            # compare the local points counter with gotten one (overflow condition)
            if input_thread_points_cnt - self.pointsCnt > STREAM_PIPE_OVERFLOW_NUM_POINTS_THRESHOLD:
                self.stop()  # stop incoming stream and flush the pipe
                self._addWarningSign()  # notify a user
                self.warningSignRemoveTimer.start()
                self.start()  # restart the stream


    def start(self):
        """
        Prepare and start a live plotting

        :return: None
        """

        # reset data cause it has changed during the pause time
        self.procVarGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))
        self.contOutGraph.curves[0].setData(self.timeAxes, np.zeros([self.nPoints]))

        self.updateTimer.start(self.interval)

        if not self._isOfflineMode:
            self.overflowCheckTimer.start(STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS)
            self.controlPipe.send(remotecontroller.InputThreadCommand.STREAM_ACCEPT)  # send command to allow stream

        self._isRun = True


    def stop(self):
        """
        Stop a live plotting and do finish routines

        :return: None
        """

        self.updateTimer.stop()

        if not self._isOfflineMode:
            self.overflowCheckTimer.stop()
            self.controlPipe.send(remotecontroller.InputThreadCommand.STREAM_REJECT)
            self.controlPipe.send(remotecontroller.InputThreadCommand.MSG_CNT_RST)  # reset remote counter

            # flush the stream pipe
            while True:
                if self.streamPipeRX.poll():
                    self.streamPipeRX.recv()
                else:
                    break

        self.pointsCnt = 0  # reset local counter
        self._isRun = False


    def toggle(self):
        """
        Toggle live plotting

        :return: None
        """

        if self._isRun:
            self.stop()
        else:
            self.start()


    def _update(self):
        """
        Routine to get a new data and plot it (i.e. redraw graphs)

        :return: None
        """

        # use fake (random) numbers in offline mode
        if self._isOfflineMode:
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
            except OSError:  # may occur during an exit mess
                pass

        # shift points array on 1 position to free up the place for a new point
        procVarData = np.roll(self.procVarGraph.curves[0].getData()[1], -1)
        procVarData[-1] = self.lastPoint['pv']
        contOutData = np.roll(self.contOutGraph.curves[0].getData()[1], -1)
        contOutData[-1] = self.lastPoint['co']

        self.procVarGraph.curves[0].setData(self.timeAxes, procVarData)
        self.contOutGraph.curves[0].setData(self.timeAxes, contOutData)

        # add the same point to the averaging label
        self.procVarAverLabel.setValue(self.lastPoint['pv'])
        self.contOutAverLabel.setValue(self.lastPoint['co'])



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

    layout = QVBoxLayout(window)
    layout.addWidget(graphs)
    layout.addWidget(graphs.procVarAverLabel)
    layout.addWidget(graphs.contOutAverLabel)

    window.show()
    sys.exit(app.exec_())
