import os
import queue
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

CHECK_CONNECTION_TIMEOUT_FIRST_CHECK = 5.0
CHECK_CONNECTION_TIMEOUT_DEFAULT = 0.1

READ_WRITE_TIMEOUT_SYNCHRONOUS = 0.1



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
    # 'co_start': 0b0011,
    # 'co_stop': 0b0010,

    'save_to_eeprom': 0b1011
}
var_cmd_reversed = {v: k for k, v in var_cmd.items()}

result = {
    'ok': 0,
    'error': 1
}
result_reversed = {v: k for k, v in result.items()}

stream_prefix = 0b00000001
# stream_prefix_reversed = {v: k for k, v in stream_prefix.items()}



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

    def __init__(self, conn=None):
        self.conn = conn
        self.pipe_rx, self.pipe_tx = multiprocessing.Pipe(duplex=False)
        self._is_run = False

    def is_run(self):
        return self._is_run

    def start(self):
        self.conn.read('stream_start')
        self._is_run = True

    def stop(self):
        self.conn.read('stream_stop')
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



def _thread_input_handler(sock_mutex, sock, var_cmd_pipe_tx, stream_pipe_tx):
# def _thread_input_handler(sock_mutex, sock, var_cmd_queue, stream_pipe_tx):

    """

    :param sock_mutex:
    :param sock:
    :param var_cmd_queue:
    :param stream_pipe_tx:
    :return:
    """

    def sigterm_handler(sig, frame):
        print(f"socket: {points_cnt}")
        sys.exit()

    signal.signal(signal.SIGTERM, sigterm_handler)

    points_cnt = 0

    while True:
        # with sock_mutex:
        available = select.select([sock], [], [], 0)

        if available[0] == [sock]:
            payload = sock.recv(BUF_SIZE)   # TODO: add timeout, also can overflow!

            response = _parse_response(payload)
            if response['var_cmd'] == 'stream':
                stream_pipe_tx.send(response['values'])  # TODO: maybe this can block, overflow!
                points_cnt += 1
            else:
                var_cmd_pipe_tx.send(response)  # TODO: this can block! maybe check queue.Full (overflow)
                # var_cmd_queue.put(response)  # TODO: this can block! maybe check queue.Full (overflow)

        time.sleep(THREAD_INPUT_HANDLER_SLEEP_TIME)



class RemoteController:
    """

    """

    isOfflineMode = False

    class Signal(QObject):
        signal = pyqtSignal()


    def __init__(self, ipAddr, udpPort, thread_pid=None):

        if thread_pid is not None:

            self.cont_ip_port = (ipAddr, udpPort)

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # TODO: wrap sock on OSError everywhere
            self.sock.settimeout(0)  # explicitly set non-blocking mode

            self.sock_mutex = multiprocessing.Lock()

            # self.var_cmd_queue = multiprocessing.Queue()
            self.var_cmd_pipe_rx, self.var_cmd_pipe_tx = multiprocessing.Pipe(duplex=False)

            self.stream = Stream(conn=self)

            self.input_handler = multiprocessing.Process(
                target=_thread_input_handler,
                args=(self.sock_mutex, self.sock, self.var_cmd_pipe_tx, self.stream.pipe_tx)
                # args = (self.sock_mutex, self.sock, self.var_cmd_queue, self.streams['pv'].pipe_tx)
            )
            self.input_handler.start()

            self.connLost = self.Signal()

            if self.checkConnection(timeout=CHECK_CONNECTION_TIMEOUT_FIRST_CHECK) != 0:
                self.isOfflineMode = True
                self.close()


    def read(self, what):
        # TODO: actually, we can calculate controller output by yourself using the same algo as in the controller
        # TODO: additionally parse the response somewhere to avoid the code like 'conn.read('coef')[0]' in the main

        if not self.isOfflineMode:

            request = _make_request('read', what)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.connLost.signal.emit()
                # TODO: return also status (maybe a whole response structure)
                return 0.0, 0.0
            return response['values']

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
            return random.random(), random.random()


    def write(self, what, *values):
        # TODO: return result code (0, 1) (and keep in mind the consistency)

        if not self.isOfflineMode:

            request = _make_request('write', what, *values)

            self.sock.sendto(request, self.cont_ip_port)
            if self.var_cmd_pipe_rx.poll(timeout=READ_WRITE_TIMEOUT_SYNCHRONOUS):
                response = self.var_cmd_pipe_rx.recv()
            else:
                self.connLost.signal.emit()
                # TODO: return also status (maybe a whole response structure)
                return result['error']
            return result[response['result']]

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
        return self.write('err_I', 0)


    def saveCurrentValues(self):
        # TODO: store configuration snapshots (so return the snapshot here and receive a snapshot as an argument at restoreValues())
        self.setpoint = self.read('setpoint')[0]
        self.Kp = self.read('kP')[0]
        self.Ki = self.read('kI')[0]
        self.Kd = self.read('kD')[0]
        self.PerrLimits = self.read('err_P_limits')
        self.IerrLimits = self.read('err_I_limits')


    def restoreValues(self):
        # TODO: return values and checks everewhere!
        self.write('setpoint', self.setpoint)
        self.write('kP', self.Kp)
        self.write('kI', self.Ki)
        self.write('kD', self.Kd)
        self.write('err_P_limits', self.PerrLimits[0], self.PerrLimits[1])
        self.write('err_I_limits', self.IerrLimits[0], self.IerrLimits[1])


    def saveToEEPROM(self):
        # TODO: check output
        return self.read('save_to_eeprom')[0]


    def checkConnection(self, timeout=CHECK_CONNECTION_TIMEOUT_DEFAULT):
        request = _make_request('read', 'setpoint')

        # try:
        #     self.sock_mutex.release()
        #     print('need to release')
        # except:
        #     pass

        self.sock.sendto(request, self.cont_ip_port)  # TODO: check socket reliability on test simple program
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


    def close(self):
        self.stream.close()
        # self.var_cmd_queue.close()
        self.var_cmd_pipe_rx.close()
        self.var_cmd_pipe_tx.close()
        self.input_handler.terminate()
        self.sock.close()



if __name__ == '__main__':

    main_thread_pid = os.getpid()
    print(main_thread_pid)
    conn = RemoteController('127.0.0.1', 1200, thread_pid=main_thread_pid)

    conn.stream.start()

    for i in range(10):
        if conn.stream.pipe_rx.poll():
            point = conn.stream.pipe_rx.recv()
            print(point)
        else:
            time.sleep(0.5)

    conn.close()
