"""
graphs.py - PyQtGraph fast widget to display live plots


STREAM_PIPE_OVERFLOW_NUM_POINTS_THRESHOLD
    number of stream points (vector with multiple values) representing difference between numbers of incoming and
    plotted points that we consider an overflow

STREAM_PIPE_OVERFLOW_CHECK_TIME_PERIOD_MS
    overflow checking timer period in milliseconds

STREAM_PIPE_OVERFLOW_WARNING_SIGN_DURATION
    time for which an overflow warning sign will be displayed


CustomGraphicsLayoutWidget
    PyQtGraph fast widget to display live plots
"""

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
            self, names: tuple=("Process Variable", "Controller Output"), numPoints: int=200, interval: int=17,
            ranges: tuple=((-2.0, 2.0), (-2.0, 2.0)), units: tuple=('Monkeys', 'Parrots'),
            controlPipe: multiprocessing.connection.Connection=None,
            streamPipeRX: multiprocessing.connection.Connection=None,
            theme: str='dark',
    ):
        """
        Graphs' constructor. Lengths of tuple arguments should be equal and each item in them should respectively match
        others

        :param names: tuple of strings with graphs' names
        :param numPoints: number of points in each graph
        :param interval: time in ms to force the plot refresh
        :param ranges: tuple of tuples with (min,max) values of each plot respectively
        :param units: tuple of strings representing measurement unit of each plot
        :param controlPipe: multiprocessing.Connection instance to communicate with a stream source
        :param streamPipeRX: multiprocessing.Connection instance from where new points should arrive
        :param theme: string representing visual appearance of the widget ('light' or 'dark')
        """

        # lengths of tuple arguments should be equal
        assert len(names) == len(ranges) == len(units)

        # need to set a theme before any other pyqtgraph operations
        if theme != 'dark':
            pyqtgraph.setConfigOption('background', 'w')
            pyqtgraph.setConfigOption('foreground', 'k')

        super(CustomGraphicsLayoutWidget, self).__init__()


        self.nPoints = numPoints
        self.pointsCnt = 0
        self.lastPoint = np.zeros(len(names))
        self.interval = interval

        self.names = list(names)  # for usage outside the class
        self.ranges = list(ranges)

        # X (time) axis is "starting" at the right border (current time) and goes to the past to the left (negative
        # time). It remains the same for an entire Graphs lifetime
        self.timeAxes = np.linspace(-numPoints * interval, 0, numPoints)


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
        for name, range in zip(names, ranges):
            if name == names[-1]:
                graph = self.addPlot(y=np.zeros(numPoints), labels={'right': name, 'bottom': "Time, ms"}, pen='r')
            else:
                graph = self.addPlot(y=np.zeros(numPoints), labels={'right': name}, pen='r')
            graph.setRange(yRange=range)
            graph.hideButtons()
            graph.hideAxis('left')
            graph.showGrid(x=True, y=True, alpha=0.2)
            self.graphs.append(graph)
            self.nextRow()

        # label widget accumulating incoming values and calculating an average from last 'averageTime' seconds
        self.averageLabels = []
        for name, unit in zip(names, units):
            averageLabel = pyqtgraph.ValueLabel(siPrefix=True, suffix=unit, averageTime=numPoints * interval * 0.001)
            averageLabel.setToolTip(f"Average {name} value of last {averageLabel.averageTime:.2f}s")
            self.averageLabels.append(averageLabel)


        # data receiving and plots redrawing timer
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self._update)

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
        for point, graph, averageLabel in zip(self.lastPoint, self.graphs, self.averageLabels):
            data = np.roll(graph.curves[0].getData()[1], -1)
            data[-1] = point
            graph.curves[0].setData(self.timeAxes, data)
            averageLabel.setValue(point)



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    from PyQt5.QtWidgets import QWidget, QApplication
    import sys

    app = QApplication(sys.argv)
    window = QWidget()

    graphs = CustomGraphicsLayoutWidget()
    graphs.start()

    layout = QVBoxLayout(window)
    layout.addWidget(graphs)
    for label in graphs.averageLabels:
        layout.addWidget(label)

    window.show()
    sys.exit(app.exec_())
