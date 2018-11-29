import copy
import datetime
import enum
import sys
import signal
import socket
import struct
import ctypes
import time
import multiprocessing
import select
import random

from PyQt5.QtCore import QObject, pyqtSignal  # TODO: migrate to native Python signals to avoid PyQt dependencies



BUF_SIZE = 9
FLOAT_SIZE = 4

THREAD_INPUT_HANDLER_SLEEP_TIME = 0.005

CHECK_CONNECTION_TIMEOUT_FIRST_CHECK = 2.0
CHECK_CONNECTION_TIMEOUT_DEFAULT = 1.0

READ_WRITE_TIMEOUT_SYNCHRONOUS = 1.0



class _Response(ctypes.Structure):
    _fields_ = [
        ('stream', ctypes.c_uint8, 2),  # LSB
        ('result', ctypes.c_uint8, 1),
        ('var_cmd', ctypes.c_uint8, 4),
        ('opcode', ctypes.c_uint8, 1)  # MSB
    ]

class _ResponseByte(ctypes.Union):
    _anonymous_ = ("bit",)
    _fields_ = [
        ("bit", _Response),
        ("asByte", ctypes.c_uint8)
    ]

class _Request(ctypes.Structure):
    _fields_ = [
        ('_reserved', ctypes.c_uint8, 3),  # LSB
        ('var_cmd', ctypes.c_uint8, 4),
        ('opcode', ctypes.c_uint8, 1)  # MSB
    ]


opcode = {  # TODO: migrate to enums?..
    'read': 0,
    'write': 1
}
opcode_reversed = {v: k for k, v in opcode.items()}

var_cmd = {
    'setpoint': 0b0100,

    'kP': 0b0101,
    'kI': 0b0110,
    'kD': 0b0111,

    'err_I': 0b1000,

    'err_P_limits': 0b1001,
    'err_I_limits': 0b1010,

    'stream_start': 0b0001,
    'stream_stop': 0b0000,

    'save_to_eeprom': 0b1011
}
var_cmd_reversed = {v: k for k, v in var_cmd.items()}

result = {
    'ok': 0,
    'error': 1
}
result_reversed = {v: k for k, v in result.items()}

stream_prefix = 0b00000001



def _make_request(operation: str, variable_command: str, *values) -> bytearray:
    """
    h

    :param operation:
    :param variable_command:
    :param values:
    :return:
    """

    request = _Request()
    request.opcode = opcode[operation]
    request.var_cmd = var_cmd[variable_command]

    request_buf = bytes(request)
    for val in values:
        request_buf += struct.pack('f', float(val))

    return request_buf


def _parse_response(response_buf: bytearray) -> dict:
    """
    Parse the buffer received from the controller to extract opcode (as a string), status (as a string),
    variable/command (as a string) and supplied values (if present)

    :param response_buf: bytearray received over the network
    :return: dict(str, str, str, list)
    """

    response_byte = _ResponseByte()
    response_byte.asByte = response_buf[0]

    if response_byte.stream:
        response_dict = {
            'opcode': 'read',
            'var_cmd': 'stream',
            'result': 'ok',
            'values': list(struct.unpack('ff', response_buf[1:2*FLOAT_SIZE + 1]))
        }
    else:
        response_dict = {
            'opcode': opcode_reversed[response_byte.opcode],
            'var_cmd': var_cmd_reversed[response_byte.var_cmd],
            'result': result_reversed[response_byte.result],
            'values': [struct.unpack('f', float_num)[0] for float_num in [response_buf[1:2*FLOAT_SIZE+1][i:i + FLOAT_SIZE] for i in range(0, 2*FLOAT_SIZE, FLOAT_SIZE)]]
        }

    return response_dict



class Stream:
    """
    Class representing the stream from the RemoteController (e.g. plot data)
    """

    class RemoteController:
        """Mock to help function annotations parser"""
        pass

    def __init__(self, connection: RemoteController=None):
        """
        Initialize the Stream instance. It does not opening the stream itself. Use pipe_rx and pipe_tx counterparts in
        outer code to assign source and sink of a stream pipe

        :param connection: RemoteController instance to bind with
        """
        self.connection = connection
        self.pipe_rx, self.pipe_tx = multiprocessing.Pipe(duplex=False)
        self._msg_counter = 0
        self._is_run = False  # TODO: getter and setter (via @property decorator)

    def is_run(self):
        return self._is_run

    def start(self):
        self.connection.read('stream_start')
        self._is_run = True

    def stop(self):
        self.connection.read('stream_stop')
        self._is_run = False

    def toggle(self):
        if self._is_run:
            self.stop()
        else:
            self.start()

    def close(self):
        self.stop()
        self.pipe_rx.close()
        self.pipe_tx.close()



@enum.unique
class InputThreadCommand(enum.Enum):
    """
    Simple instruction set to control the input thread

    Notes
    Unfortunately we cannot subclass Pipe because this is a function returning 2 Connection objects to add some useful
    properties and methods.
    Ideally, it would be great to have built-in counter and accept/reject flag in Stream class. There will be no need in
    such instruction set as all operations will be performing through this meta-object. We can check for overflow "on
    the spot" too, Graph class would be simpler. After all, general architecture would be nicer. The problem is to
    somehow [gracefully] pass the Stream object (or its part) to the thread
    """
    MSG_CNT_GET = enum.auto()
    MSG_CNT_RST = enum.auto()
    STREAM_ACCEPT = enum.auto()
    STREAM_REJECT = enum.auto()


def _thread_input_handler(
    input_lock:        multiprocessing.Lock,
    sock:              socket.socket,
    control_pipe:      multiprocessing.Pipe,
    var_cmd_pipe_tx:   multiprocessing.Pipe,
    stream_pipe_tx:    multiprocessing.Pipe
) -> None:

    """
    Routine is intended to be running in the background as a thread and listening to all incoming messages. Maximum
    receive time is determined by THREAD_INPUT_HANDLER_SLEEP_TIME variable. The function then performs a basic parsing
    to determine a type of the message and route it to the corresponding pipe.
    No other thread should listen to the given socket at the same time. Use 'input_lock' argument to pass the locking
    mutex.
    Listening to pipes threads are responsible for overflow detection and correction. Use 'control_pipe' to send/receive
    service messages and control thread execution.
    Thread is normally terminated by SIGTERM signal

    :param input_lock: mutex to pause/resume the execution
    :param sock: socket instance to listen
    :param control_pipe: send/receive service messages over this
    :param var_cmd_pipe_tx: transmission part of the pipe for delivering messages like 'setpoint' and 'err_I_limits'
    :param stream_pipe_tx: transmission part of the pipe for delivering streaming values (e.g. for plotting). Take care
    to not overflow it!
    :return: None
    """

    def sigterm_handler(sig, frame):
        sys.exit()

    signal.signal(signal.SIGTERM, sigterm_handler)

    stream_accept = True
    stream_msg_cnt = 0

    while True:
        with input_lock:  # TODO: replace Lock with simple boolean (deliver via control_pipe (better control_queue))

            # poll a socket for available data and return immediately (last argument is a timeout)
            available = select.select([sock], [], [], 0)
            if available[0] == [sock]:
                try:
                    payload = sock.recv(BUF_SIZE)
                    response = _parse_response(payload)
                except ConnectionResetError:  # meet on Windows
                    sigterm_handler('sig', 'frame')  # dummy values

                if response['var_cmd'] == 'stream':
                    if stream_accept:
                        stream_pipe_tx.send(response['values'])
                        stream_msg_cnt += 1
                else:
                    var_cmd_pipe_tx.send(response)

        # check whether there are any service messages (non-blocking mode)
        if control_pipe.poll():
            command = control_pipe.recv()
            if command == InputThreadCommand.MSG_CNT_GET:
                control_pipe.send(stream_msg_cnt)
            elif command == InputThreadCommand.MSG_CNT_RST:
                stream_msg_cnt = 0
            elif command == InputThreadCommand.STREAM_REJECT:
                stream_accept = False
            elif command == InputThreadCommand.STREAM_ACCEPT:
                stream_accept = True

        # sleep all remaining time and repeat
        time.sleep(THREAD_INPUT_HANDLER_SLEEP_TIME)



# use this standardized dictionary to fill snapshots
snapshot_template = {
    'date': 'datetime.datetime.now()',

    'setpoint': 0.0,
    'kP': 0.0,
    'kI': 0.0,
    'kD': 0.0,
    'err_P_limits': [-1.0, 1.0],
    'err_I_limits': [-1.0, 1.0]
}



class _BaseException(Exception):

    def __init__(self, operation):
        super(_BaseException, self).__init__()
        self.operation = operation

    def __str__(self):
        return f"Invalid operation '{self.operation}'"


class RequestInvalidOperationException(_BaseException):
    pass


class ResponseException(_BaseException):

    def __init__(self, operation, thing, values):
        super(ResponseException, self).__init__(operation)
        self.thing = thing
        self.values = values

    def __str__(self):
        return f"RemoteController has responded with error code for operation '{self.operation}' on '{self.thing}', "\
                "supplied values: " + str(self.values)


class ResponseMismatchException(_BaseException):

    def __init__(self, operation, got, expected, values):
        super(ResponseMismatchException, self).__init__(operation)
        self.got = got
        self.expected = expected
        self.values = values

    def __str__(self):
        return f"operation '{self.operation}': expected '{self.expected}', got '{self.got}', supplied values: " +\
               str(self.values)


class RequestKeyException(_BaseException):

    def __init__(self, operation, key):
        super(RequestKeyException, self).__init__(operation)
        self.key = key

    def __str__(self):
        return f"Invalid key '{self.key}' for operation '{self.operation}'"



class Signal(QObject):
    """
    Base for creating QT signals (such as ConnectionLost). Use it as follows:

        somethingHappened = Signal()
        somethingHappened.signal.connect(somethingHappenedHandler)
        ...

        somethingHappened.signal.emit()

        ...
        @pyqtSlot()
        def somethingHappenedHandler():
            ...

    """

    signal = pyqtSignal()



class RemoteController:
    """
    Straightforward interface to the remote PID controller. Can operate both in 'online' (real connection is present)
    and 'offline' (replacing real values by fake random data) mode
    """

    def __init__(self, ip_addr: str, udp_port: int):
        """
        Initialization of the RemoteController class

        Notes
        We can use Queue here instead of the Pipe. It seems to be more suited for this application due to its a little
        bit nicer waiting interface. Pipe is faster though but the variable/command stream is not so heavy-loaded also

            self.var_cmd_queue = multiprocessing.Queue()

        For example, RemoteController.read(what) function in this case will looks like:

            try:
                self.sock.sendto(request, self.cont_ip_port)
                response = self.var_cmd_queue.get(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS)
            except (queue.Empty, OSError):
                self.conn_lost.signal.emit()
                self._parse_response(what)
            else:
                self._parse_response(what, response=response)

        At the same time in the input thread:

            var_cmd_queue.put(response)

        :param ip_addr: string representing IP-address of the controller' network interface
        :param udp_port: integer representing UDP port of the controller' network interface
        """

        self.snapshots = []  # currently only one snapshot is created and used

        self.is_offline_mode = False
        self.cont_ip_port = (ip_addr, udp_port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # TODO: wrap sock on OSError everywhere
        self.sock.settimeout(0)  # explicitly set the non-blocking mode

        self.input_thread_mutex = multiprocessing.Lock()
        self.input_thread_control_pipe_main, self.input_thread_control_pipe_thread = multiprocessing.Pipe(duplex=True)

        self.var_cmd_pipe_rx, self.var_cmd_pipe_tx = multiprocessing.Pipe(duplex=False)

        self.stream = Stream(connection=self)

        self.input_handler = multiprocessing.Process(
            target=_thread_input_handler,
            args=(
                self.input_thread_mutex,
                self.sock,
                self.input_thread_control_pipe_thread,
                self.var_cmd_pipe_tx,
                self.stream.pipe_tx
            )
        )
        self.input_handler.start()

        self.conn_lost = Signal()

        # use recently started thread to check an actual connection and if it is not present close all the related stuff
        if self.check_connection(timeout=CHECK_CONNECTION_TIMEOUT_FIRST_CHECK) != 0:
            self.is_offline_mode = True
            self.close()

        # explicitly stop the stream in case it somehow was active
        self.stream.stop()


    @staticmethod
    def _parse_response(what: str, response: dict=None):
        """
        Additional wrapper around the _parse_response() function performing more deep inspection of what we got from
        the controller and what we should return to the caller in accordance to parsed data. Raises some exceptions
        in case of detected errors

        :param what: string representing expected RemoteController' variable or command
        :param response: response dictionary (_parse_response() output)
        :return: int or [int, int] in accordance with the requested data
        """

        if response is not None:
            # online mode - parse the response

            if response['result'] == 'error':
                raise ResponseException(response['opcode'], response['var_cmd'], response['values'])
            if response['var_cmd'] != what:
                raise ResponseMismatchException(response['opcode'], response['var_cmd'], what, response['values'])

            if response['opcode'] == 'read':
                if response['var_cmd'] in ['setpoint', 'kP', 'kI', 'kD', 'err_I']:
                    return response['values'][0]
                elif response['var_cmd'] in ['err_P_limits', 'err_I_limits']:
                    return response['values']
                elif response['var_cmd'] in ['save_to_eeprom', 'stream_start', 'stream_stop']:
                    return result[response['result']]  # 'ok'
            else:
                return result[response['result']]  # 'ok'

        else:
            # offline mode - provide fake (random) data

            if what in ['setpoint', 'kP', 'kI', 'kD', 'err_I']:
                return random.random()
            elif what in ['err_P_limits', 'err_I_limits']:
                return random.random(), random.random()
            elif what in ['save_to_eeprom', 'stream_start', 'stream_stop']:
                return result['error']


    @staticmethod
    def _make_request(operation: str, what: str, *values) -> bytearray:
        """
        Additional wrapper around the _make_request() function that checks some parameters. Raises some exceptions in
        case of detected errors

        :param operation: string representing an operation ('read' or 'write')
        :param what: string representing RemoteController' variable or command
        :param values: (optional) supplied values (for 'write' operation)
        :return: bytearray request
        """

        if operation not in ['read', 'write']:
            raise RequestInvalidOperationException(operation)

        # check for valid key
        if what not in var_cmd.keys():
            raise RequestKeyException(operation, what)

        # for reading all keys are allowed so we check only writing
        if operation == 'write':
            if what in ['stream_start', 'stream_stop', 'save_to_eeprom']:
                raise RequestKeyException(operation, what)
            elif what == 'err_I' and values[0] != 0.0:
                raise ValueError("'err_I' allows only reading and reset (writing 0.0), got " + str(values))

        return _make_request(operation, what, *values)


    def read(self, what: str) -> int:
        """
        Read a variable from the controller. Synchronous function, waits for the reply from the controller via the
        'var_cmd_pipe' (waiting timeout is READ_WRITE_TIMEOUT_SYNCHRONOUS)

        :param what: string representing the variable to be read
        :return: result['error'] or result['ok'] (int)
        """

        if not self.is_offline_mode:

            request = self._make_request('read', what)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.conn_lost.signal.emit()
                return self._parse_response(what)
            return self._parse_response(what, response=response)

        else:
            return self._parse_response(what)


    def write(self, what: str, *values) -> int:
        """
        Write a variable to the controller. Synchronous function, waits for the reply from the controller via the
        'var_cmd_pipe' (waiting timeout is READ_WRITE_TIMEOUT_SYNCHRONOUS)

        :param what: string representing the variable to be written
        :param values: (optional) numbers supplied with a request
        :return: result['error'] or result['ok'] (int)
        """

        if not self.is_offline_mode:

            request = self._make_request('write', what, *values)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.conn_lost.signal.emit()
                return result['error']
            return self._parse_response(what, response)

        else:
            return result['ok']


    def reset_i_err(self) -> int:
        """
        Resets an accumulated integral error of the PID algorithm

        :return: result['error'] or result['ok'] (int)
        """

        return self.write('err_I', 0.0)


    def save_current_values(self) -> None:
        """
        Saves current PID parameters in the snapshot dictionary, supplies it with a current date and store the result
        in the 'snapshots' list (instance attribute)

        :return: None
        """

        snapshot = copy.deepcopy(snapshot_template)
        for key in snapshot.keys():
            if key != 'date':
                snapshot[key] = self.read(key)
        snapshot['date'] = datetime.datetime.now()
        self.snapshots.append(snapshot)


    def restore_values(self, snapshot: dict) -> None:
        """
        Gets PID values from the given snapshot dictionary and writes them into the controller. This does not write
        values to the EEPROM

        :param snapshot: special dictionary representing a single snapshot
        :return: None
        """

        for key, value in snapshot.items():
            if key != 'date':  # snapshot has an accessory 'date' key
                self.write(key, value)


    def save_to_eeprom(self) -> int:
        """
        Saves current PID-related values to controller's EEPROM

        :return: result['error'] or result['ok'] (int)
        """

        return self.read('save_to_eeprom')


    def check_connection(self, timeout=CHECK_CONNECTION_TIMEOUT_DEFAULT) -> int:
        """
        Check the connection. The function sends the request to read a 'setpoint' and waits for the response from the
        input listening thread. Therefore a usage is possible only in 'online' mode

        :param timeout: timeout (default is CHECK_CONNECTION_TIMEOUT_DEFAULT)
        :return: result['error'] or result['ok'] (int)
        """

        request = _make_request('read', 'setpoint')  # use setpoint as a test request

        if not self.is_offline_mode:
            try:
                self.sock.sendto(request, self.cont_ip_port)
            except OSError:
                # probably PC has no network
                self.is_offline_mode = True
                return result['error']

            if self.var_cmd_pipe_rx.poll(timeout=timeout):
                self.var_cmd_pipe_rx.recv()  # receive the message to keep the pipe clean
            else:
                self.is_offline_mode = True
                return result['error']

            self.is_offline_mode = False

        return result['ok']


    def pause(self) -> None:
        """
        Lock the mutex blocking the input listening thread so its main loop cannot run no more

        :return: None
        """

        self.input_thread_mutex.acquire()


    def resume(self) -> None:
        """
        Unlock the mutex blocking the input listening thread

        :return: None
        """

        try:
            self.input_thread_mutex.release()
        except ValueError:
            pass


    def close(self) -> None:
        """
        "Close" the entire connection in a sense of the "online" communication: socket, input thread, pipes etc.
        RemoteController though will still be able to provide fake (random) data to simulate the behavior of a real
        connection

        :return: None
        """

        self.stream.close()

        self.var_cmd_pipe_rx.close()
        self.var_cmd_pipe_tx.close()

        self.input_thread_control_pipe_main.close()
        self.input_thread_control_pipe_thread.close()

        self.input_handler.terminate()

        self.sock.close()



if __name__ == '__main__':
    """
    You can use this block for testing purposes (run the module as a standalone script)
    """

    conn = RemoteController('127.0.0.1', 1200)

    # conn.stream.start()
    #
    # for i in range(10):
    #     if conn.stream.pipe_rx.poll():
    #         point = conn.stream.pipe_rx.recv()
    #         print(point)
    #     else:
    #         time.sleep(0.5)
    #
    # conn.close()

    # try:
    # raise RequestInvalidOperationException('read')
    # except ResponseException as e:
    #     print(e)
