import socket
import subprocess
import re
import os
import json
import socketserver

from config import settings

ACTION_CODE = {
    '1000': 'cmd',
    '2000': 'post',
    '3000': 'get'
}

REQUEST_CODE = {
    '1001': 'cmd info',
    '1002': 'cmd ack',
    '2001': 'post info',
    '2002': 'ACK (File can be uploaded',
    '2003': 'File has existed',
    '2004': 'Continue transfer',
    '2005': 'Do not continue transfer',
    '3001': 'get info',
    '4001': 'Unauthorized',
    '4002': 'Authorize successfully',
    '4003': 'Authorize failed'
}

class Server(object):
    request_queue_size = 5

    def __init__(self):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_bind(settings.BIND_HOST, settings.BIND_PORT)
            self.server_active()
        except Exception as e:
            print(e)
            self.server_close()

    def server_bind(self, ip, port):
        self.socket.bind(ip, port,)

    def server_active(self):
        self.socket.listen(self.request_queue_size)
        self.run()

    def server_close(self):
        self.socket.close()

    def run(self):
        while True:
            conn, address = self.socket.accept()
            conn.sendall(bytes('Welcome to login', 'utf-8'))
            obj = Action(conn)
            while True:
                client_bytes = conn.recv(1024)
                if not client_bytes:
                    break

                client_str = str(client_bytes, encoding='utf-8')
                if obj.has_login:
                    o = client_str.split('|', 1)
                    if len(o) > 0:
                        func = getattr(obj, o[0])
                        func(client_str)
                    else:
                        conn.sendall(bytes('Wrong format', 'utf8'))
                else:
                    obj.login(client_str)

            conn.close()


class MultiServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        conn = self.request
        conn.sendall(bytes('Welcome login', 'utf-8'))
        obj = Action(conn)

        while True:
            client_bytes = conn.recv(1024)
            if not client_bytes:
                break

            client_str = str(client_bytes, encoding='utf-8')
            if obj.has_login:
                o = client_str.split('|', 1)
                if len(o) > 0:
                    func = getattr(obj, o[0])
                    func(client_str)
                else:
                    conn.sendalll(bytes('Wrong format', 'utf-8'))
            else:
                obj.login(client_str)

        conn.close()


class MultiServer(object):
    def __init__(self):
        server = socketserver.ThreadingTCPServer((settings.BIND_HOST, settings.BIND_PORT), MultiServerHandler)
        server.serve_forever()


class Action(object):
    def __init__(self, conn):
        self.conn = conn
        self.has_login = False
        self.username = None
        self.home = None
        self.current_dir = None

    def login(self,origin):
        self.conn.sendall(bytes("4001", 'utf-8'))
        while True:
            login_str = str(self.conn.recv(1024), encoding='utf-8')
            login_dict = json.loads(login_str)
            if login_dict['username'] == 'wupeiqi' and login_dict['pwd'] == '123':
                self.conn.sendall(bytes('4002', 'utf-8'))
                self.has_login = True
                self.username = 'wupeiqi'
                self.initialize()
                break
            else:
                self.conn.sendall(bytes('4003', 'utf-8'))

    def initialize(self):
        self.home = os.path.join(settings.USER_HOME, self.username)
        self.current_dir = os.path.join(settings.USER_HOME, self.username)

    def cmd(self, origin):

        func, command = origin.split('|', 1)
        command_list = re.split('\s*',command, 1)

        if command_list[0] == 'ls':
            if len(command_list) == 1:
                if self.current_dir:
                    command_list.append(self.current_dir)
                else:
                    command_list.append(self.home)
            else:
                if self.current_dir:
                    p = os.path.join(self.current_dir, command_list[1])
                else:
                    p = os.path.join(self.home, command_list)
                command_list[1] = p

        if command_list[1] == 'cd':
            if len(command_list) == 1:
                command_list.append(self.home)
            else:
                if self.current_dir:
                    p = os.path.join(self.current_dir, command_list[1])
                else:
                    p = os.path.join(self.home, command_list[1])
                self.current_dir = p
                command_list[1] = p

        command = ' '.join(command_list)

        try:
            result_bytes = subprocess.check_output(command, shell=True)
            result_bytes = bytes(str(result_bytes, encoding='utf-8'), encoding='utf-8')
        except Exception as e:
            result_bytes = bytes('error cmd', encoding='utf-8')

        info_str = "info|%d" % len(result_bytes)
        self.conn.sendall(bytes(info_str, 'utf-8'))
        ack = self.conn.recv(1024)
        self.conn.sendall(result_bytes)

    def post(self, origin):
        func, file_bytes_size, file_name, fine_md5, target_path = origin.split('|', 4)
        target_abs_md5_path = os.path.join(self.home, target_path)
        has_receive = 0
        file_bytes_size = int(file_bytes_size)

        if os.path.exists(target_abs_md5_path):
            self.conn.sendall(bytes('2003', 'utf-8'))
            is_continue = str(self.conn.recv(1024), 'utf-8')
            if is_continue == "2004":
                has_file_size = os.stat(target_abs_md5_path).st_size
                self.conn.sendall(bytes(str(has_file_size), 'utf-8'))
                has_receive += has_file_size
                f = open(target_abs_md5_path, 'ab')

            else:
                f = open(target_abs_md5_path, 'wb')

        else:
            self.conn.sendall(bytes('2002', 'utf-8'))
            f =open(target_abs_md5_path, 'wb')

        while file_bytes_size > has_receive:
            data = self.conn.recv(1024)
            f.write(data)
            has_receive += len(data)
        f.close()

    def get(self, origin):
        pass

    def exit(self, origin):
        pass




