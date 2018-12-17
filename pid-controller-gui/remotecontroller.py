"""
remotecontroller.py - standalone interface to the remote PID controller with zero external dependencies


const REMOTECONTROLLER_MSG_SIZE
    message size (in bytes) to and from the remote controller (same for commands, values, stream messages)
const FLOAT_SIZE
    float type representation size (in bytes)
const THREAD_INPUT_HANDLER_SLEEP_TIME
    sleep time between incoming messages processing (in seconds)
const CHECK_CONNECTION_TIMEOUT_FIRST_CHECK
    timeout for the first check only (in seconds)
const CHECK_CONNECTION_TIMEOUT_DEFAULT
    timeout for all following checks (in seconds)
const READ_WRITE_TIMEOUT_SYNCHRONOUS
    though input listening thread is running asynchronously we retrieve and send non-stream data in a synchronous manner


class _Response
class _Request
    C-type bitfields representing RemoteController response and request respectively. Make parsing and construction
    easier

class _ResponseByte
    C-type union allows to represent the byte both as a value and as a bitfield specified earlier

dict opcode
dict var_cmd
dict result
int stream_prefix
    instruction set constants in form of dictionary

dict opcode_swapped
dict var_cmd_swapped
dict result_swapped
    value-key swapped dictionaries for parsing and other tasks

function _make_request
function _parse_response
    core functions to construct the request and parse the response respectively (additional checks are performed in
    respective RemoteController methods)

class Stream
    class representing the stream from the RemoteController (e.g. plot data)

enum InputThreadCommand
    commands to control the input listening thread

function _thread_input_handler
    function to run as multiprocessing.Process target that receives all incoming data from the given socket and cast to
    respective listeners from the main thread via pipes

dict snapshot_template
    PID values snapshot dictionary with attached datetime (template)

exception _BaseExceptions
exception RequestInvalidOperationException
exception ResponseException
exception ResponseVarCmdMismatchException
exception ResponseOperationMismatchException
exception RequestKeyException
    module's exceptions to raise in case of error

class RemoteController
    class combining defined earlier instruments in a convenient high-level interface
"""

import copy
import datetime
import enum
import sys
import socket
import struct
import ctypes
import time
import multiprocessing
import select
import random



#
# buffers sizes in bytes
#
REMOTECONTROLLER_MSG_SIZE = 9
FLOAT_SIZE = 4

#
# timeouts in seconds
#
THREAD_INPUT_HANDLER_SLEEP_TIME = 0.005

CHECK_CONNECTION_TIMEOUT_FIRST_CHECK = 2.0
CHECK_CONNECTION_TIMEOUT_DEFAULT = 1.0

READ_WRITE_TIMEOUT_SYNCHRONOUS = 1.0



class _Response(ctypes.Structure):
    """Bitfield structure for easy parsing of responses from the remote controller"""
    _fields_ = [
        ('stream', ctypes.c_uint8, 2),  # LSB
        ('result', ctypes.c_uint8, 1),
        ('var_cmd', ctypes.c_uint8, 4),
        ('opcode', ctypes.c_uint8, 1)  # MSB
    ]

class _ResponseByte(ctypes.Union):
    """Union allows to represent a byte as a bitfield"""
    _anonymous_ = ("bit",)
    _fields_ = [
        ("bit", _Response),
        ("asByte", ctypes.c_uint8)
    ]

class _Request(ctypes.Structure):
    """Bitfield to easy construct the request byte"""
    _fields_ = [
        ('_reserved', ctypes.c_uint8, 3),  # LSB
        ('var_cmd', ctypes.c_uint8, 4),
        ('opcode', ctypes.c_uint8, 1)  # MSB
    ]


opcode = {
    'read': 0,
    'write': 1
}
opcode_swapped = {value: key for key, value in opcode.items()}

_VAR_CMD_STREAM = 65535
var_cmd = {
    # variables
    'setpoint': 0b0100,

    'kP': 0b0101,
    'kI': 0b0110,
    'kD': 0b0111,

    'err_I': 0b1000,

    'err_P_limits': 0b1001,
    'err_I_limits': 0b1010,

    # commands - send them only in 'read' mode
    'stream_start': 0b0001,
    'stream_stop': 0b0000,

    'save_to_eeprom': 0b1011,

    # stream
    'stream': _VAR_CMD_STREAM
}
var_cmd_swapped = {value: key for key, value in var_cmd.items()}

# Use the same dictionary to parse controller' responses and as return value of functions so use it from other modules
# for comparisons as well
result = {
    'ok': 0,
    'error': 1
}
result_swapped = {value: key for key, value in result.items()}

stream_prefix = 0b00000001  # every stream message should be prefaced with such byte



def _make_request(operation: str, variable_command: str, *values) -> bytearray:
    """
    Prepare the request bytearray for sending to the controller using given operation, variable/command and (optional)
    values (for writing only)

    :param operation: string representing operation ('read' or 'write')
    :param variable_command: string representing variable or command
    :param values: (optional) numbers to write
    :return: request bytearray
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
            'opcode': opcode['read'],
            'var_cmd': var_cmd['stream'],
            'result': result['ok']
        }
    else:
        response_dict = {
            'opcode': opcode_swapped[response_byte.opcode],
            'var_cmd': var_cmd_swapped[response_byte.var_cmd],
            'result': result_swapped[response_byte.result]
        }

    response_dict['values'] = list(struct.unpack('ff', response_buf[1:2*FLOAT_SIZE + 1]))

    return response_dict



class Stream:
    """Class representing the stream from the RemoteController (e.g. plot data)"""

    class RemoteController:
        """Mock for function annotations"""
        pass

    def __init__(self, connection: RemoteController=None):
        """
        Initialize the Stream instance inside a given RemoteController. It does not opening the stream itself. Use
        pipe_rx and pipe_tx counterparts in outer code to assign source and sink of a stream pipe

        :param connection: RemoteController instance to bind with
        """
        self.connection = connection
        self.pipe_rx, self.pipe_tx = multiprocessing.Pipe(duplex=False)
        self._msg_counter = 0
        self._is_run = False

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
    somehow [gracefully] share or pass the Stream object (or its part) to the thread
    """

    MSG_CNT_GET = enum.auto()
    MSG_CNT_RST = enum.auto()

    STREAM_ACCEPT = enum.auto()
    STREAM_REJECT = enum.auto()

    INPUT_ACCEPT = enum.auto()
    INPUT_REJECT = enum.auto()

    EXIT = enum.auto()


def _thread_input_handler(
    sock:              socket.socket,
    control_pipe:      multiprocessing.Pipe,
    var_cmd_pipe_tx:   multiprocessing.Pipe,
    stream_pipe_tx:    multiprocessing.Pipe
) -> None:

    """
    Routine is intended to be running in the background as a thread and listening to all incoming messages. Maximum
    receive time is determined by THREAD_INPUT_HANDLER_SLEEP_TIME variable. The function then performs a basic parsing
    to determine a type of the message and route it to the corresponding pipe.
    No other thread should listen to the given socket at the same time. Use 'stream_accept' flag to block the execution.
    Listening to pipes threads are responsible for overflow detection and correction. Use 'control_pipe' to send/receive
    service messages and control thread execution.
    Thread is normally terminated by SIGTERM signal

    :param sock: socket instance to listen
    :param control_pipe: send/receive service messages over this
    :param var_cmd_pipe_tx: transmission part of the pipe for delivering messages like 'setpoint' and 'err_I_limits'
    :param stream_pipe_tx: transmission part of the pipe for delivering streaming values (e.g. for plotting). Take care
    to not overflow it!
    :return: None
    """

    input_accept = True

    stream_accept = True
    stream_msg_cnt = 0

    while True:
        if input_accept:

            # poll a socket for available data and return immediately (last argument is a timeout)
            available = select.select([sock], [], [], 0)
            if available[0] == [sock]:
                try:
                    payload = sock.recv(REMOTECONTROLLER_MSG_SIZE)
                except ConnectionResetError:  # meet on Windows
                    sys.exit()

                response = _parse_response(payload)
                if response['var_cmd'] == var_cmd['stream']:
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
            elif command == InputThreadCommand.INPUT_REJECT:
                input_accept = False
            elif command == InputThreadCommand.INPUT_ACCEPT:
                input_accept = True
            elif command == InputThreadCommand.EXIT:
                sys.exit()

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
    """Basis exception - 'operation' is used by all sub-exceptions"""

    def __init__(self, operation):
        super(_BaseException, self).__init__()
        self.operation = operation


class RequestInvalidOperationException(_BaseException):

    def __str__(self):
        return f"Invalid operation '{self.operation}'"


class RequestKeyException(_BaseException):

    def __init__(self, operation, key):
        super(RequestKeyException, self).__init__(operation)
        self.key = key

    def __str__(self):
        return f"Invalid key '{self.key}' for operation '{self.operation}'"


class ResponseException(_BaseException):

    def __init__(self, operation, thing, values):
        super(ResponseException, self).__init__(operation)
        self.thing = thing
        self.values = values

    def __str__(self):
        return f"RemoteController has responded with error code for operation '{self.operation}' on '{self.thing}', " \
                "supplied values: " + str(self.values)


class ResponseVarCmdMismatchException(_BaseException):

    def __init__(self, operation, got, expected, values):
        super(ResponseVarCmdMismatchException, self).__init__(operation)
        self.got = got
        self.expected = expected
        self.values = values

    def __str__(self):
        return f"operation '{self.operation}': expected '{self.expected}', got '{self.got}', supplied values: " + \
               str(self.values)


class ResponseOperationMismatchException(_BaseException):

    def __init__(self, op_got, op_expected, thing, values):
        super(ResponseOperationMismatchException, self).__init__(op_expected)
        self.op_got = op_got
        self.thing = thing
        self.values = values

    def __str__(self):
        return f"'{self.thing}': requested '{self.operation}', got '{self.op_got}', supplied values: " + \
               str(self.values)



class RemoteController:
    """
    Straightforward interface to the remote PID controller. Can operate both in 'online' (real connection is present)
    and 'offline' (replacing real values by fake random data) mode
    """

    def __init__(self, ip_addr: str, udp_port: int, conn_lost_signal=None):
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
        :param conn_lost_signal: [optional] PyQt signal to emit when the connection is lost during the read/write
        operations. Otherwise the disconnect could only be revealed by an explicit call to check_connection() method
        """

        self.snapshots = []  # currently only one snapshot is created and used

        self._is_offline_mode = False
        self.cont_ip_port = (ip_addr, udp_port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0)  # explicitly set the non-blocking mode

        self.input_thread_control_pipe_main,\
        self.input_thread_control_pipe_thread = multiprocessing.Pipe(duplex=True)

        self.var_cmd_pipe_rx,\
        self.var_cmd_pipe_tx = multiprocessing.Pipe(duplex=False)

        self.stream = Stream(connection=self)

        self.input_thread = multiprocessing.Process(
            target=_thread_input_handler,
            args=(
                self.sock,
                self.input_thread_control_pipe_thread,
                self.var_cmd_pipe_tx,
                self.stream.pipe_tx
            )
        )
        self.input_thread.start()

        self.conn_lost_signal = conn_lost_signal

        # use recently started thread to check an actual connection and if it is not present close all the related stuff
        if self.check_connection(timeout=CHECK_CONNECTION_TIMEOUT_FIRST_CHECK) == result['error']:
            self._is_offline_mode = True
            self.close()
        else:
            self.stream.stop()  # explicitly stop the stream in case it somehow was active


    @property
    def is_offline_mode(self):
        """getter of the read-only property"""
        return self._is_offline_mode


    @staticmethod
    def _parse_response(operation: str, what: str, response: dict=None):
        """
        Additional wrapper around the _parse_response() function performing more deep inspection of what we got from
        the controller and what we should return to the caller in accordance to parsed data. Raises some exceptions
        in case of detected errors

        :param operation: string representing an operation ('read' or 'write')
        :param what: string representing expected RemoteController' variable or command
        :param response: response dictionary (_parse_response() output)
        :return: int or [int, int] in accordance with the requested data
        """

        # online mode - parse the response
        if response is not None:

            if response['result'] == 'error':
                raise ResponseException(response['opcode'], response['var_cmd'], response['values'])
            if response['opcode'] != operation:
                raise ResponseOperationMismatchException(response['opcode'], operation, response['var_cmd'],
                                                         response['values'])
            if response['var_cmd'] != what:
                raise ResponseVarCmdMismatchException(response['opcode'], response['var_cmd'], what, response['values'])

            if response['opcode'] == 'read':
                if response['var_cmd'] in ['setpoint', 'kP', 'kI', 'kD', 'err_I']:
                    return response['values'][0]
                elif response['var_cmd'] in ['err_P_limits', 'err_I_limits']:
                    return response['values']
                elif response['var_cmd'] in ['save_to_eeprom', 'stream_start', 'stream_stop']:
                    return result[response['result']]  # 'ok'
            else:
                return result[response['result']]  # 'ok'

        # offline mode - provide fake (random) data
        else:

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

        if operation not in opcode.keys():
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

        if not self._is_offline_mode:

            request = self._make_request('read', what)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self._is_offline_mode = True
                if self.conn_lost_signal is not None:
                    self.conn_lost_signal.emit()
                return self._parse_response('read', what)
            return self._parse_response('read', what, response=response)

        else:
            return self._parse_response('read', what)


    def write(self, what: str, *values) -> int:
        """
        Write a variable to the controller. Synchronous function, waits for the reply from the controller via the
        'var_cmd_pipe' (waiting timeout is READ_WRITE_TIMEOUT_SYNCHRONOUS)

        :param what: string representing the variable to be written
        :param values: (optional) numbers supplied with a request
        :return: result['error'] or result['ok'] (int)
        """

        if not self._is_offline_mode:

            request = self._make_request('write', what, *values)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self._is_offline_mode = True
                if self.conn_lost_signal is not None:
                    self.conn_lost_signal.emit()
                return result['error']
            return self._parse_response('write', what, response)

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


    def restore_values(self, snapshot: dict) -> datetime.datetime:
        """
        Gets PID values from the given snapshot dictionary and writes them into the controller. This does not writes
        values to the EEPROM

        :param snapshot: special dictionary representing a single snapshot
        :return: datetime.datetime object of the restored snapshot
        """

        for key, value in snapshot.items():
            if key != 'date':  # snapshot has an accessory 'date' key
                if isinstance(value, list):
                    self.write(key, *value)
                else:
                    self.write(key, value)

        return snapshot['date']


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

        try:
            self.sock.sendto(request, self.cont_ip_port)
        except OSError:  # probably PC has no network
            self._is_offline_mode = True
            return result['error']

        if self.var_cmd_pipe_rx.poll(timeout=timeout):
            self.var_cmd_pipe_rx.recv()  # receive the message to keep the pipe clean
        else:
            self._is_offline_mode = True
            return result['error']

        self._is_offline_mode = False
        return result['ok']


    def pause(self) -> None:
        """
        Stop listening to any incoming messages

        :return: None
        """

        if not self._is_offline_mode:
            self.input_thread_control_pipe_main.send(InputThreadCommand.INPUT_REJECT)


    def resume(self) -> None:
        """
        Resume listening to any incoming messages

        :return: None
        """

        if not self._is_offline_mode:
            self.input_thread_control_pipe_main.send(InputThreadCommand.INPUT_ACCEPT)


    def close(self) -> None:
        """
        "Close" the entire connection in a sense of the "online" communication: socket, input thread, pipes etc.
        RemoteController though will still be able to provide fake (random) data to simulate the behavior of a real
        connection

        :return: None
        """

        if not self._is_offline_mode:
            self.stream.close()

        self.var_cmd_pipe_rx.close()
        self.var_cmd_pipe_tx.close()

        if self.input_thread.is_alive():
            self.input_thread_control_pipe_main.send(InputThreadCommand.EXIT)

        self.input_thread_control_pipe_main.close()
        self.input_thread_control_pipe_thread.close()

        self.sock.close()



if __name__ == '__main__':
    """
    Use this block for testing purposes (run the module as a standalone script)
    """

    conn = RemoteController('127.0.0.1', 1200)
    print('offline mode:', conn.is_offline_mode)

    print('setpoint:', conn.read('setpoint'))

    print('some stream values:')
    conn.stream.start()
    for i in range(50):
        if conn.stream.pipe_rx.poll():
            point = conn.stream.pipe_rx.recv()
            print(point)
        else:
            time.sleep(0.005)

    conn.close()
