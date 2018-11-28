import copy
import datetime
import os
# import queue
import sys
import signal
import socket
import struct
import ctypes
import time
import multiprocessing
import select
import random

from PyQt5.QtCore import QObject, pyqtSignal



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


opcode = {
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
            # 'var_cmd': stream_prefix_reversed[response_byte.stream],
            'result': 'ok',
            'values': list(struct.unpack('ff', response_buf[1:2*FLOAT_SIZE + 1]))
            # 'values': [struct.unpack('f', response_buf[1:FLOAT_SIZE + 1])[0]]
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
    Version for single-value stream:

        class Stream:

            def __init__(self, name, conn=None):
                self.name = name
                self.conn = conn
                self.pipe_rx, self.pipe_tx = multiprocessing.Pipe(duplex=False)
                self._is_run = False

            def is_run(self):
                return self._is_run

            def start(self):
                self.conn.read(f'{self.name}_start')
                self._is_run = True

            def stop(self):
                self.conn.read(f'{self.name}_stop')
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

    """

    def __init__(self, connection=None):
        self.connection = connection
        self.pipe_rx, self.pipe_tx = multiprocessing.Pipe(duplex=False)
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



def _thread_input_handler(input_lock, sock, control_pipe, var_cmd_pipe_tx, stream_pipe_tx):
# def _thread_input_handler(sock_mutex, sock, var_cmd_queue, stream_pipe_tx):

    def sigterm_handler(sig, frame):
        # print(f"socket: {stream_msg_cnt}")
        sys.exit()

    signal.signal(signal.SIGTERM, sigterm_handler)

    stream_allowed = True
    stream_msg_cnt = 0

    while True:
        with input_lock:

            available = select.select([sock], [], [], 0)
            if available[0] == [sock]:
                try:
                    payload = sock.recv(BUF_SIZE)
                    response = _parse_response(payload)
                except ConnectionResetError:  # Windows exception
                    sigterm_handler(0, 0)

                if response['var_cmd'] == 'stream':
                    if stream_allowed:
                        stream_pipe_tx.send(response['values'])
                        stream_msg_cnt += 1
                else:
                    var_cmd_pipe_tx.send(response)
                    # var_cmd_queue.put(response)

            if control_pipe.poll():
                cmd = control_pipe.recv()
                if cmd == 'get':
                    control_pipe.send(stream_msg_cnt)
                elif cmd == 'rst':
                    stream_allowed = False
                    stream_msg_cnt = 0
                elif cmd == 'run':
                    stream_allowed = True


        time.sleep(THREAD_INPUT_HANDLER_SLEEP_TIME)


snapshot_template = {
    'date': 'datetime.datetime.now()',

    'setpoint': 0.0,
    'kP': 0.0,
    'kI': 0.0,
    'kD': 0.0,
    'err_P_limits': [-1.0, 1.0],
    'err_I_limits': [-1.0, 1.0]
}



class RemoteControllerException(Exception):

    def __init__(self, operation, thing, values):
        super(RemoteControllerException, self).__init__()
        self.operation = operation
        self.thing = thing
        self.values = values

    def __str__(self):
        return f"operation '{self.operation}' on '{self.thing}', supplied values: " + str(self.values)


class MismatchException(Exception):

    def __init__(self, operation, got, expected, values):
        super(MismatchException, self).__init__()
        self.operation = operation
        self.got = got
        self.expected = expected
        self.values = values

    def __str__(self):
        return f"operation '{self.operation}': expected '{self.expected}', got '{self.got}'. Supplied values: " +\
               str(self.values)


class RequestKeyException(Exception):

    def __init__(self, operation, key):
        super(RequestKeyException, self).__init__()
        self.operation = operation
        self.key = key

    def __str__(self):
        return f"Invalid key '{self.key}' for operation '{self.operation}'"


class RemoteController:
    """

    """

    class Signal(QObject):
        signal = pyqtSignal()


    def __init__(self, ipAddr, udpPort):

        self.snapshots = []  # currently only one snapshot is created and used

        self.isOfflineMode = False
        self.cont_ip_port = (ipAddr, udpPort)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # TODO: wrap sock on OSError everywhere
        self.sock.settimeout(0)  # explicitly set non-blocking mode

        self.input_thread_mutex = multiprocessing.Lock()
        self.input_thread_control_pipe_main, self.input_thread_control_pipe_thread = multiprocessing.Pipe(duplex=True)

        # self.var_cmd_queue = multiprocessing.Queue()
        self.var_cmd_pipe_rx, self.var_cmd_pipe_tx = multiprocessing.Pipe(duplex=False)

        self.stream = Stream(connection=self)

        self.input_handler = multiprocessing.Process(
            target=_thread_input_handler,
            args=(self.input_thread_mutex, self.sock, self.input_thread_control_pipe_thread, self.var_cmd_pipe_tx, self.stream.pipe_tx)
            # args = (self.sock_mutex, self.sock, self.var_cmd_queue, self.streams['pv'].pipe_tx)
        )
        self.input_handler.start()

        self.connLost = self.Signal()

        if self.checkConnection(timeout=CHECK_CONNECTION_TIMEOUT_FIRST_CHECK) != 0:
            self.isOfflineMode = True
            self.close()

        self.stream.stop()


    def _parse_response(self, what, response=None):
        if response is not None:
            # online mode

            if response['result'] == 'error':
                raise RemoteControllerException(response['opcode'], response['var_cmd'], response['values'])
            if response['var_cmd'] != what:
                raise MismatchException(response['opcode'], response['var_cmd'], what, response['values'])

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
            # offline mode - fake data

            if what in ['setpoint', 'kP', 'kI', 'kD', 'err_I']:
                return random.random()
            elif what in ['err_P_limits', 'err_I_limits']:
                return random.random(), random.random()
            elif what in ['save_to_eeprom', 'stream_start', 'stream_stop']:
                return result['error']


    def _make_request(self, operation, what, *values):
        if what not in var_cmd.keys():
            raise RequestKeyException(operation, what)

        return _make_request(operation, what, *values)


    def read(self, what):
        # TODO: actually, we can calculate controller output by yourself using the same algo as in the controller
        # TODO: additionally parse the response somewhere to avoid the code like 'conn.read('coef')[0]' in the main

        if not self.isOfflineMode:

            request = self._make_request('read', what)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.connLost.signal.emit()
                # TODO: return also status (maybe a whole response structure)
                return self._parse_response(what)
            return self._parse_response(what, response=response)

            # try:
            #     # with self.sock_mutex:
            #     self.sock.sendto(request, self.cont_ip_port)
            #     response = self.var_cmd_queue.get(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS)
            # except (queue.Empty, OSError):
            #     self.connLost.signal.emit()
            #     # TODO: return also status (maybe a whole response structure)
            #     return 0.0, 0.0
            # else:
            #     return response['values']

        else:
            return self._parse_response(what)


    def write(self, what, *values):
        # TODO: return result code (0, 1) (and keep in mind the consistency)

        if not self.isOfflineMode:

            request = self._make_request('write', what, *values)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.connLost.signal.emit()
                # TODO: return also status (maybe a whole response structure)
                return result['error']
            return self._parse_response(what, response)

            # try:
            #     # with self.sock_mutex:
            #     self.sock.sendto(request, self.cont_ip_port)
            #     response = self.var_cmd_queue.get(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS)  # TODO: give this and other constants a VARIABLE
            # except (queue.Empty, OSError):
            #     self.connLost.signal.emit()
            #     return result['error']
            # else:
            #     return result[response['result']]

        else:
            return result['ok']


    def resetIerr(self):
        return self.write('err_I', 0.0)


    def saveCurrentValues(self):
        snapshot = copy.deepcopy(snapshot_template)
        for key, value in snapshot.items():
            if key != 'date':
                value = self.read(key)
        snapshot['date'] = datetime.datetime.now()
        self.snapshots.append(snapshot)

        # TODO: store configuration snapshots (so return the snapshot here and receive a snapshot as an argument at restoreValues())
        # self.setpoint = self.read('setpoint')[0]
        # self.Kp = self.read('kP')[0]
        # self.Ki = self.read('kI')[0]
        # self.Kd = self.read('kD')[0]
        # self.PerrLimits = self.read('err_P_limits')
        # self.IerrLimits = self.read('err_I_limits')


    def restoreValues(self, snapshot):
        for key, value in snapshot.items():
            if key != 'date':
                self.write(key, value)

        # TODO: return values and checks everewhere!
        # self.write('setpoint', self.setpoint)
        # self.write('kP', self.Kp)
        # self.write('kI', self.Ki)
        # self.write('kD', self.Kd)
        # self.write('err_P_limits', self.PerrLimits[0], self.PerrLimits[1])
        # self.write('err_I_limits', self.IerrLimits[0], self.IerrLimits[1])


    def saveToEEPROM(self):
        return self.read('save_to_eeprom')


    def checkConnection(self, timeout=CHECK_CONNECTION_TIMEOUT_DEFAULT):
        request = _make_request('read', 'setpoint')

        # try:
        #     self.sock_mutex.release()
        #     print('need to release')
        # except:
        #     pass

        try:
            self.sock.sendto(request, self.cont_ip_port)  # TODO: check socket reliability on test simple program
        except OSError:
            self.isOfflineMode = True
            return 1

        if self.var_cmd_pipe_rx.poll(timeout=timeout):
            self.var_cmd_pipe_rx.recv()
        else:
            self.isOfflineMode = True
            return 1
        self.isOfflineMode = False
        return 0

        # try:
        #     # if self.sock_mutex.acquire(block=False, timeout=timeout):
        #     #     self.sock.sendto(request, self.cont_ip_port)
        #     #     self.sock_mutex.release()
        #     # else:
        #     #     self.sock_mutex.release()  # BAD!
        #     #     print('locked')
        #     #     return 1
        #     # with self.sock_mutex:  # TODO: add timeout here for lock.acquire()
        #     self.sock.sendto(request, self.cont_ip_port)  # TODO: check socket reliability on test simple program
        #         # print('mutex unlocked')
        #     self.var_cmd_queue.get(timeout=timeout)
        # except (queue.Empty, OSError):
        #     self.isOfflineMode = True
        #     return 1
        # else:
        #     self.isOfflineMode = False
        #     return 0


    def pause(self):
        self.input_thread_mutex.acquire()


    def resume(self):
        try:
            self.input_thread_mutex.release()
        except ValueError:
            pass


    def close(self):
        self.stream.close()

        # self.var_cmd_queue.close()
        self.var_cmd_pipe_rx.close()
        self.var_cmd_pipe_tx.close()

        self.input_thread_control_pipe_main.close()
        self.input_thread_control_pipe_thread.close()

        self.input_handler.terminate()

        self.sock.close()



if __name__ == '__main__':

    # TODO: test with server and client over LAN

    # conn = RemoteController('127.0.0.1', 1200)
    #
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

    try:
        raise RemoteControllerException('read', 'kP', [-18.4, 19.7])
    except RemoteControllerException as e:
        print(e)
