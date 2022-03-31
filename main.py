import sys
import socket
import threading
from enum import Enum

LOCALHOST = '127.0.0.1'
FIRST_PORT = 20001
TCS = 10
TP = 10


class State(Enum):
    HELD = 0,
    WANTED = 1,
    DO_NOT_WANT = 2


class Process(threading.Thread):

    def __init__(self, pid: int, port: int, other_ports: set):
        super().__init__()
        self.pid = f'P{pid}'
        self.others = [(LOCALHOST, p) for p in other_ports]
        self.state = State.DO_NOT_WANT
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket(port)

    def init_socket(self, port: int):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((LOCALHOST, port))
        self.socket.settimeout(10)
        self.socket.listen(1)

    def broadcast(self, message: bytes):
        for address in self.others:
            self.send_to_process(address, message)

    def send_to_process(self, address: tuple, message: bytes):
        pass

    def run(self):
        pass


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
        p.start()
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
