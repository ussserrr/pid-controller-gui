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


# SOCK_TIMEOUT = 5.0  # seconds
BUF_SIZE = 9
FLOAT_SIZE = 4



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

    'pv_start': 0b0001,
    'pv_stop': 0b0000,
    'co_start': 0b0011,
    'co_stop': 0b0010,

    'save_to_eeprom': 0b1011
}
var_cmd_reversed = {v: k for k, v in var_cmd.items()}

result = {
    'ok': 0,
    'error': 1
}
result_reversed = {v: k for k, v in result.items()}

stream_prefix = {
    'pv': 0b00000001,
    'co': 0b00000010
}
stream_prefix_reversed = {v: k for k, v in stream_prefix.items()}



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
            'var_cmd': stream_prefix_reversed[response_byte.stream],
            'result': 'ok',
            'values': [struct.unpack('f', response_buf[1:FLOAT_SIZE + 1])[0]]
        }
    else:
        response_dict = {
            'opcode': opcode_reversed[response_byte.opcode],
            'var_cmd': var_cmd_reversed[response_byte.var_cmd],
            'result': result_reversed[response_byte.result],
            'values': [struct.unpack('f', float_num)[0] for float_num in [response_buf[1:2*FLOAT_SIZE+1][i:i + FLOAT_SIZE] for i in range(0, 2*FLOAT_SIZE, FLOAT_SIZE)]]
        }

    return response_dict



def _thread_input_handler(lock, sock, queue_var, queue_pv):

    cnt = 0

    def term_handler(sig, frame):
        print(f"pv points: {cnt}")
        sys.exit()

    signal.signal(signal.SIGTERM, term_handler)

    while True:
        with lock:
            available = select.select([sock], [], [], 0)

            if available[0] == [sock]:
                payload = sock.recv(BUF_SIZE)

                response = _parse_response(payload)
                if response['var_cmd'] == 'pv':
                    queue_pv.put(response)
                    cnt += 1
                else:
                    queue_var.put(response)

        time.sleep(0.005)


# def _thread_pv_stream_handler(lock, queue_pv):
#
#     def _sigterm_handler(sig, frame):
#         sys.exit()
#
#     signal.signal(signal.SIGTERM, _sigterm_handler)
#
#     while True:
#         try:
#             pv = queue_pv.get(timeout=0.1)
#             with lock:
#                 print(pv)
#         except queue.Empty:
#             pass



class RemoteController():

    isOfflineMode = False

    class Signal(QObject):
        signal = pyqtSignal()


    def __init__(self, ipAddr, udpPort, thread_pid=None):

        if thread_pid is not None:

            self.cont_ip_port = (ipAddr, udpPort)

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_mutex = multiprocessing.Lock()

            self.queue_var = multiprocessing.Queue()
            self.queue_pv = multiprocessing.Queue()

            self.input_handler = multiprocessing.Process(
                target=_thread_input_handler,
                args=(self.sock_mutex, self.sock, self.queue_var, self.queue_pv)
            )
            self.input_handler.start()

            # self.pv_stream_handler = multiprocessing.Process(target=_thread_pv_stream_handler, args=(self.sock_mutex, queue_pv))
            # self.pv_stream_handler.start()


            self.connLost = self.Signal()


            if self.checkConnection(timeout=5.0) != 0:
                self.isOfflineMode = True
                self.sock.close()
                self.input_handler.terminate()


    def read(self, what):
        # TODO: actually, we can calculate controller output by yourself using the same algo as in the controller
        # TODO: additionally parse the response somewhere to avoid the code like 'conn.read('coef')[0]' in the main

        if not self.isOfflineMode:

            request = _make_request('read', what)
            try:
                with self.sock_mutex:
                    self.sock.sendto(request, self.cont_ip_port)
                response = self.queue_var.get(timeout=0.1)
            except (queue.Empty, OSError):
                self.connLost.signal.emit()
                # TODO: return also status (maybe a whole response structure)
                return 0.0, 0.0
            else:
                return response['values']

        else:
            return random.random(), random.random()


    def write(self, what, *values):
        # TODO: return result code (0, 1) (and keep in mind the consistency)

        if not self.isOfflineMode:

            request = _make_request('write', what, *values)
            try:
                with self.sock_mutex:
                    self.sock.sendto(request, self.cont_ip_port)
                response = self.queue_var.get(timeout=0.1)  # TODO: give this and other constants a VARIABLE
            except (queue.Empty, OSError):
                self.connLost.signal.emit()
                return result['error']
            else:
                return result[response['result']]

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
        return self.read('save_to_eeprom')


    def checkConnection(self, timeout=0.1):
        request = _make_request('read', 'setpoint')
        try:
            with self.sock_mutex:
                self.sock.sendto(request, self.cont_ip_port)
            self.queue_var.get(timeout=timeout)
        except (queue.Empty, OSError):
            return 1
        else:
            return 0


    def close(self):
        self.input_handler.terminate()
        self.queue_var.close()
        self.sock.close()



if __name__ == '__main__':

    print("Hello")
    # import os
    # main_thread_pid = os.getppid()
    #
    # queue_var = multiprocessing.Queue()
    # cont_ip_port = ('127.0.0.1', 1200)
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock_mutex = multiprocessing.Lock()
    #
    # queue_pv = multiprocessing.Queue()
    #
    # input_handler = multiprocessing.Process(target=_thread_input_handler,
    #                                         args=(sock_mutex, sock, queue_var, queue_pv))
    # input_handler.start()
    #
    #
    # rc = RemoteController('127.0.0.1', 1200, main_thread_pid)
    # print(rc.checkConnection())
    # print(rc.checkConnection())

    # request = _make_request('read', 'setpoint')
    # with sock_mutex:
    #     sock.sendto(request, cont_ip_port)
    # try:
    #     val = queue_var.get(timeout=SOCK_TIMEOUT)
    #     print(val)
    # except queue.Empty:
    #     print("except queue.Empty")
    #
    # request = _make_request('read', 'setpoint')
    # with sock_mutex:
    #     sock.sendto(request, cont_ip_port)
    # try:
    #     val = queue_var.get(timeout=SOCK_TIMEOUT)
    #     print(val)
    # except queue.Empty:
    #     print("except queue.Empty")
