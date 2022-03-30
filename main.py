import sys


class Process:
    pass


if __name__ == '__main__':
    N = int(sys.argv[1])
    if N <= 0:
        print('Number of processes should be positive integer.')
        exit(1)
    while True:
        command = input('$ ').split(' ')
        if command[0] == 'list':
            pass
        elif command[0] == 'time-cs':
            t = int(command[1])
        elif command[0] == 'time-p':
            t = int(command[1])
        elif command[0] == 'exit':
            break
        else:
            print('Unknown command')
