import sys
import time
import socket
import _thread
import threading
import numpy as np
from enum import Enum
from queue import Queue

LOCALHOST = '127.0.0.1'
FIRST_PORT = 20001
TCS = 10
TP = 5


class State(Enum):
    HELD = 0,
    WANTED = 1,
    DO_NOT_WANT = 2


class Process:

    def __init__(self, pid: int, port: int, other_ports: set):
        super().__init__()
        self.pid = f'P{pid}'
        self.port = port
        self.state = State.DO_NOT_WANT
        self.timestamp = 0
        self.queue = Queue()
        self.terminated = threading.Event()
        self.others = [(LOCALHOST, prt) for prt in other_ports]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket(port)

    def init_socket(self, port: int):
        self.socket.bind((LOCALHOST, port))
        self.socket.listen()

    def stop(self):
        self.terminated.set()

    @staticmethod
    def tp_timeout():
        return np.random.randint(5, TP + 1)

    @staticmethod
    def tcs_timeout():
        return np.random.randint(10, TCS + 1)

    @staticmethod
    def decode_request(data: bytes):
        pid, t = data.decode().strip().split(' ')
        return pid, int(t)

    @staticmethod
    def ok_response():
        return 'OK'.encode()

    @staticmethod
    def send_to_process(address: tuple, message: str):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)
        sock.send(message.encode())
        result = sock.recv(1024).decode()
        return result == "OK"

    def apply_for_cs(self):
        while not self.terminated.is_set():
            time.sleep(self.tp_timeout())
            self.state = State.WANTED
            self.timestamp += 1
            message = f'{self.pid} {self.timestamp}'
            for address in self.others:
                self.send_to_process(address, message)
            self.state = State.HELD
            time.sleep(self.tcs_timeout())
            self.state = State.DO_NOT_WANT
            while not self.queue.empty():
                flag = self.queue.get()
                flag.set()

    def handle_connection(self, conn):
        pid, t = self.decode_request(conn.recv(1024))
        if self.state == State.WANTED:
            if t > self.timestamp:
                ready = threading.Event()
                self.queue.put(ready)
                ready.wait()
        elif self.state == State.HELD:
            ready = threading.Event()
            self.queue.put(ready)
            ready.wait()
        conn.sendall(self.ok_response())

    def start(self):
        _thread.start_new_thread(self.apply_for_cs, ())
        while not self.terminated.is_set():
            conn, _ = self.socket.accept()
            _thread.start_new_thread(self.handle_connection, (conn,))


def init_processes(n: int):
    ports = {FIRST_PORT + i for i in range(n)}
    return [Process(i+1, FIRST_PORT+i, ports - {FIRST_PORT+i}) for i in range(n)]


if __name__ == '__main__':
    N = int(sys.argv[1])
    if N <= 0:
        print('Number of processes should be positive integer.')
        exit(1)
    processes = init_processes(N)
    for p in processes:
        _thread.start_new_thread(p.start, ())
    while True:
        command = input('$ ').split(' ')
        if command[0] == 'list':
            p_list = [f'{process.pid}, {process.state.name}' for process in processes]
            print(*p_list, sep='\n')
        elif command[0] == 'time-cs':
            TCS = int(command[1])
        elif command[0] == 'time-p':
            TP = int(command[1])
        elif command[0] == 'exit':
            break
        else:
            print('Unknown command')
    for p in processes:
        p.stop()
