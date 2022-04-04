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
        self.pid = pid
        self.port = port
        self.state = State.DO_NOT_WANT
        self.timestamp = 0
        self.sent_timestamp = 0
        self.queue = Queue()
        self.terminated = threading.Event()
        self.others = [(LOCALHOST, prt) for prt in other_ports]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket(port)

    def init_socket(self, port: int):
        """
        Init input socket and listen on it
        """
        self.socket.bind((LOCALHOST, port))
        self.socket.listen()

    @staticmethod
    def tp_timeout():
        """
        Calculate random waiting timeout
        """
        return np.random.randint(5, TP + 1)

    @staticmethod
    def tcs_timeout():
        """
        Calculate random CS possession timeout
        """
        return np.random.randint(10, TCS + 1)

    @staticmethod
    def decode_request(data: bytes):
        """
        Decode incoming request
        """
        pid, t = data.decode().strip().split(' ')
        return int(pid), int(t)

    @staticmethod
    def ok_response():
        """
        OK response
        """
        return 'OK'.encode()

    def to_queue(self, pid, t):
        """
        In lecture 6 it was not defined what to do when the timestamps match,
        therefore I added a rule, that in such case a process with lower
        id wins. Otherwise it would create a deadlock.
        Source: http://www2.imm.dtu.dk/courses/02222/Spring_2011/W9L2/Chapter_12a.pdf (slide 36).
        """
        return (t, pid) > (self.sent_timestamp, self.pid)

    @staticmethod
    def send_to_process(address: tuple, message: str):
        """
        Connect to other process, send a message and wait for reply
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)
        sock.send(message.encode())
        result = sock.recv(128).decode()
        return result == "OK"

    def broadcast_and_wait(self, message):
        """
        Broadcast a message to other processes and wait for reply
        """
        sent_threads = []
        for address in self.others:
            new_thread = threading.Thread(target=self.send_to_process, args=(address, message))
            sent_threads.append(new_thread)
            new_thread.start()
        for thread in sent_threads:
            thread.join()

    def possess(self):
        """
        Hold the critical section and release
        """
        self.state = State.HELD
        time.sleep(self.tcs_timeout())
        self.state = State.DO_NOT_WANT

    def handle_critical_section(self):
        """
        Apply for critical section when it's time, possess it and notify
        queued processes in a loop
        """
        while not self.terminated.is_set():
            time.sleep(self.tp_timeout())
            self.timestamp += 1
            self.sent_timestamp = self.timestamp
            message = f'{self.pid} {self.sent_timestamp}'
            self.state = State.WANTED
            self.broadcast_and_wait(message)
            self.possess()
            while not self.queue.empty():
                flag = self.queue.get()
                flag.set()

    def handle_connection(self, conn):
        """
        Handle new connection: reply OK on the conditions of
        Ricart-Agrawala algorithm
        """
        pid, t = self.decode_request(conn.recv(1024))
        self.timestamp = max(t, self.timestamp) + 1
        if self.state == State.HELD or self.state == State.WANTED and self.to_queue(pid, t):
            ready = threading.Event()
            self.queue.put(ready)
            ready.wait()
        conn.sendall(self.ok_response())
        conn.close()

    def start(self):
        """
        Process starting point, initiates all the processes
        """
        _thread.start_new_thread(self.handle_critical_section, ())
        while not self.terminated.is_set():
            conn, _ = self.socket.accept()
            _thread.start_new_thread(self.handle_connection, (conn,))
        self.socket.close()

    def stop(self):
        """
        Raises termination flag
        """
        self.terminated.set()


def init_processes(n: int):
    """
    Creates n processes, assigning them to ports [20001:20000+N]
    """
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
            p_list = [f'P{process.pid}, {process.state.name}' for process in processes]
            print(*p_list, sep='\n')
        elif command[0] == 'time-cs':
            TCS = int(command[1])
        elif command[0] == 'time-p':
            TP = int(command[1])
        elif command[0] in ['exit', 'quit']:
            break
        else:
            print('Unknown command')
    for p in processes:
        p.stop()
