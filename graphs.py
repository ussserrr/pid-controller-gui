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
            self, names: tuple=('ABC', 'DEF'), nPoints: int=200, interval: int=17,
            ranges: tuple=((-1.0, 1.0), (-1.0, 1.0)), units: tuple=('lol', 'kek'),
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
        self.lastPoint = np.zeros(len(names))
        self.interval = interval

        self.ranges = list(ranges)

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

        self.graphs = []
        for idx, name in enumerate(names):
            if name == names[-1]:
                self.graphs.append(self.addPlot(y=np.zeros(nPoints), labels={'bottom': "Time, ms",
                                                                             'right': name}, pen='r'))
            else:
                self.graphs.append(self.addPlot(y=np.zeros(nPoints), labels={'right': name}, pen='r'))
            self.graphs[idx].setRange(yRange=ranges[idx])
            self.graphs[idx].hideButtons()
            self.graphs[idx].hideAxis('left')
            self.graphs[idx].showGrid(x=True, y=True, alpha=0.2)
            self.nextRow()

        # label widget accumulating incoming values and calculating an average from last 'averageTime' seconds
        self.averageLabels = []
        for unit in units:
            self.averageLabels.append(pyqtgraph.ValueLabel(siPrefix=True, suffix=unit,
                                                           averageTime=nPoints*interval*0.001))

        # data receiving and plots redrawing timer
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self._update)

        self.pointsCnt = 0

        # notify a user about an overflow by a red circle appearing in an upper-left corner of the plot canvas
        self._warningSign = None
        self.warningSignRemoveTimer = QTimer()
        self.warningSignRemoveTimer.setSingleShot(True)
        self.warningSignRemoveTimer.setInterval(STREAM_PIPE_OVERFLOW_WARNING_SIGN_DURATION)
        self.warningSignRemoveTimer.timeout.connect(self._removeWarningSign)


    @property
    def isRun(self) -> bool:
        """bool property getter"""
        return self._isRun


    def _addWarningSign(self) -> None:
        """
        Notify a user about an overflow by a red circle appearing in an upper-left corner of the plot canvas

        :return: None
        """

        self._warningSign = self.graphs[0].plot(y=[self.ranges[0][1]*0.75], x=[-self.nPoints*self.interval*0.95],
                                                   symbol='o', symbolSize=24, symbolPen='r', symbolBrush='r')

    def _removeWarningSign(self) -> None:
        """
        Notify a user about an overflow by a red circle appearing in an upper-left corner of the plot canvas (callback
        for warningSignRemoveTimer.timeout slot)

        :return: None
        """

        self.graphs[0].removeItem(self._warningSign)


    def _overflowCheck(self) -> None:
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


    def start(self) -> None:
        """
        Prepare and start a live plotting

        :return: None
        """

        # reset data cause it has changed during the pause time
        for graph in self.graphs:
            graph.curves[0].setData(self.timeAxes, np.zeros(self.nPoints))

        self.updateTimer.start(self.interval)

        if not self._isOfflineMode:
            self.overflowCheckTimer.start(STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS)
            self.controlPipe.send(remotecontroller.InputThreadCommand.STREAM_ACCEPT)  # send command to allow stream

        self._isRun = True


    def stop(self) -> None:
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


    def toggle(self) -> None:
        """
        Toggle live plotting

        :return: None
        """

        if self._isRun:
            self.stop()
        else:
            self.start()


    def _update(self) -> None:
        """
        Routine to get a new data and plot it (i.e. redraw graphs)

        :return: None
        """

        # use fake (random) numbers in offline mode
        if self._isOfflineMode:
            self.lastPoint = -0.5 + np.random.random(len(self.lastPoint))
            self.pointsCnt += 1
        else:
            try:
                if self.streamPipeRX.poll():
                    point = self.streamPipeRX.recv()
                    self.lastPoint = point
                    self.pointsCnt += 1
            except OSError:  # may occur during an exit mess
                pass

        # shift points array on 1 position to free up the place for a new point
        for idx, (graph, averageLabel) in enumerate(zip(self.graphs, self.averageLabels)):
            data = np.roll(graph.curves[0].getData()[1], -1)
            data[-1] = self.lastPoint[idx]
            graph.curves[0].setData(self.timeAxes, data)
            averageLabel.setValue(self.lastPoint[idx])



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    from PyQt5.QtWidgets import QWidget, QApplication
    import sys

    app = QApplication(sys.argv)
    window = QWidget()

    graphs = CustomGraphicsLayoutWidget(names=('1', '2', '3'), ranges=((-1,1), (-1,1), (-1,1)), units=('A', 'B', 'C'))
    graphs.start()

    layout = QVBoxLayout(window)
    layout.addWidget(graphs)
    for label in graphs.averageLabels:
        layout.addWidget(label)

    window.show()
    sys.exit(app.exec_())
