import socket
import os
import re
import json
from config import settings
from lib import commons


def login(conn):
    while True:
        username = input('Please input your username(click "q" to quit): ')
        pwd = input('Please inpur your password: ')
        login_info = {'username': username, 'pwd': pwd}
        conn.sendall(bytes(json.dumps(login_info), 'utf-8'))
        received_code = str(conn.recv(1024), encoding='utf-8')
        if received_code == '4002':
            print('Authorize successfully')
            break
        else:
            print('Username or password wrong')

def cmd(conn, inp):
    conn.sendall(bytes(inp, 'utf-8'))
    basic_info_bytes = conn.recv(1024)
    basic_info_str = str(basic_info_bytes, 'utf-8')
    if basic_info_str == '4001':
        login(conn)
    else:
        conn.sendall(bytes('ack', 'utf-8'))
        print(str(basic_info_bytes, 'utf-8'))
        result_length = int(str(basic_info_bytes, 'utf-8').split('|')[1])
        has_received = 0
        content_bytes = bytes()
        while has_received < result_length:
            fetch_bytes = conn.recv(1024)
            has_received += len(fetch_bytes)
            content_bytes = fetch_bytes
        cmd_result = str(content_bytes, 'utf-8')
        print(cmd_result)


def post(conn, inp):
    method, file_paths = inp.split('|', 1)
    local_path, target_path = re.split('\s', file_paths, 1)
    file_byte_size = os.stat(local_path).st_size
    file_name = os.path.basename(local_path)
    file_md5 = commons.fetch_file_md5(local_path)

    post_info = "post|%s|%s|%s|%s" % (file_byte_size, file_name, file_md5, target_path)

    conn.sendall(bytes(post_info, 'utf-8'))

    result_exist = str(conn.recv(1024), 'utf-8')

    if result_exist == '4001':
        login(conn)
        return

    has_send = 0
    if result_exist == '2003':
        imp_continue = input('File has exist. Do you want to continue upload? Y/N')
        if imp_continue.upper() == 'Y':
            conn.sendall(bytes('2004', 'utf-8'))
            result_continue_pos = str(conn.recv(1024), 'utf-8')
            has_send = int(result_continue_pos)
        else:
            conn.sendall(bytes('2005', 'utf-8'))

    file_obj = open(local_path, 'rb')
    file_obj.seek(has_send)
    while file_byte_size > has_send:
        data = file_obj.read(1024)
        conn.sendall(data)
        has_send += len(data)
        commons.bar(has_send, file_byte_size)
    file_obj.close()
    print('Upload finished successfully')


def get(conn, imp):
    pass


def help_info():
    print('''
    cmd|command
    post|local_path remote_path
    get | file path to download 
    exit | exit
    ''')


def execute(conn):
    choice_dict = {
        'cmd': cmd,
        'get': get,
        'post': post,
    }
    help_info()
    while True:
        inp = input('Please input:  ')
        if inp == 'help':
            help_info()
            continue
        choice = inp.split('|')[0]
        if choice == 'exit':
            return
        if choice in choice_dict:
            func = choice_dict[choice]
            func(conn, inp)


def main():
    ip_port = (settings.server, settings.port)
    conn = socket.socket()
    conn.connect(ip_port)
    welcome_bytes = conn.recv(1024)
    print(str(welcome_bytes, encoding='utf-8'))

    execute(conn)

    conn.close()
