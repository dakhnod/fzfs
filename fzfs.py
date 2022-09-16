from ast import parse
from audioop import add
import errno
from fileinput import filename
from os import unlink
import pathlib
from signal import signal
from stat import S_IFDIR, ST_ATIME, ST_CTIME, ST_MODE, ST_MTIME, ST_NLINK
from turtle import back

import flipper_api
import fuse
import logging
import time
import stat
import os
import argparse
import pathlib
import serial
import serial_ble
import sys

def main():
    parser = argparse.ArgumentParser(description='FUSE driver for flipper serial connection')
    parser.add_argument('-d', '--device', help='Serial device to connect to', dest='serial_device')
    parser.add_argument('-a', '--address', help='Flipper BLE address', dest='ble_address')
    parser.add_argument('-m', '--mount', help='Mount point to mount the FZ to', dest='mountpoint', required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    mountpoint = args.mountpoint

    if not os.path.isdir(mountpoint):
        print('mountpoint must be an empty folder')
        return

    if len(os.listdir(mountpoint)) != 0:
        print('mountpoint must be an empty folder')
        return


    if args.serial_device is None and args.ble_address is None:
        print('either serial_device or ble_address required')
        return

    if args.serial_device is not None and args.ble_address is not None:
        print('only one of serial_device/ble_address required')
        return

    serial_device = None

    def create_serial_device():
        if args.serial_device is not None:
            if not os.path.exists(args.serial_device):
                print('serial device not an actual file')
                parser.print_usage()
                exit()

            return create_physical_serial(args.serial_device, True)
        if args.ble_address is not None:
            def disconnect_handler(client):
                print('disconnected')
                sys.exit(0)

            return create_ble_serial(args.ble_address, None)

    serial_device = create_serial_device()

    if serial_device is None:
        print('failed creating serial device')

    backend = FlipperZeroFileSysten(serial_device)

    fuse_started = True
    # fuse_thread = threading.Thread(target=fuse.FUSE, kwargs={'operations': backend, 'mountpoint': mountpoint, 'foreground': True})
    def fuse_start():
        fuse.FUSE(backend, mountpoint, foreground=True)

    print('starting fs...')
    fuse_start()
    print('fuse stopped')

    try:
        serial_device.stop()
        print('stopped bluetooth')
    except AttributeError:
        pass


def create_physical_serial(file, is_cli):
    s = serial.Serial(file, timeout=1)
    s.baudrate = 230400
    s.flushOutput()
    s.flushInput()
    if is_cli:
        s.read_until(b'>: ')
        s.write(b"start_rpc_session\r")
        s.read_until(b'\n')
    return s

def create_ble_serial(address, disconnected_handler):
    s = serial_ble.BLESerial(address, '19ed82ae-ed21-4c9d-4145-228e61fe0000', '19ed82ae-ed21-4c9d-4145-228e62fe0000')
    print('connecting...')
    s.start(disconnected_handler)
    print('connected')

    return s
    


class FlipperZeroFileSysten(fuse.Operations, fuse.LoggingMixIn):
    def __init__(self, serial_port) -> None:
        super().__init__()
        self.api = flipper_api.FlipperAPI(serial_port)
        self.api.connect()
        self.file_root = {
                'type': 'DIR'
            }
        self.fd = 0

    def find_child_by_name(self, parent, child_name):
            for child in parent['children']:
                if child['name'] == child_name:
                    return child
            raise fuse.FuseOSError(errno.ENOENT)

    def get_file_from_parts(self, parent, parts, index):
        def list_dir(dir_path):
            return self.api.list_directory(dir_path, {'full_path': dir_path, 'parent': parent})

        if index <= len(parts):
            full_path = f"/{'/'.join(parts[:index])}"

            if parent['type'] == 'DIR':
                try:
                    parent['children']
                except KeyError:
                    parent['children'] = list_dir(full_path)

            if index == len(parts):
                return parent

            child = self.find_child_by_name(parent, parts[index])

            return self.get_file_from_parts(child, parts, index + 1)

        return parent
        

    def get_file_by_path(self, path_full: str):
        path = path_full[:]
        if path[0] == '/':
            path = path[1:]
        if path == '':
            parts = []
        else:
            parts = path.split('/')
        
        return self.get_file_from_parts(self.file_root, parts, 0)

    def readdir(self, path, fh = None):
        # print(f'requested {path}')

        parent = self.get_file_by_path(path)

        return ['.', '..'] + [child['name'] for child in parent['children']]

    def getattr(self, path, fh=None):
        file = self.get_file_by_path(path)

        try:
            return file['attr']
        except KeyError:
            pass

        print(f'getting attr for {path}')

        now = time.time()

        attr = {
            'st_mode': 0o777,
            'st_ctime': now,
            'st_mtime': now,
            'st_atime': now
        }

        is_dir = (file['type'] == 'DIR')
            
        if is_dir:
            attr['st_mode'] |= stat.S_IFDIR
            attr['st_nlink'] = 2
        else:
            response = self.api.stat(path)
            attr['st_size'] = response['size']
            attr['st_mode'] |= stat.S_IFREG
            attr['st_nlink'] = 1

        
        file['attr'] = attr

        return attr

    def read(self, path, size, offset, fh):
        cached = self.get_file_by_path(path)

        try:
            return bytes(cached['contents'][offset:offset + size])
        except KeyError:
            pass

        data = None

        print(f'reading {path}')

        data = self.api.read_file_contents(path)['data']

        cached['contents'] = data
        return bytes(data[offset:offset + size])

    def write(self, path, data, offset, fh):
        print(f'write file: {path} offset: {offset} length: {len(data)}')
        try:
            cached = self.get_file_by_path(path)
        except OSError:
            self.create(path, None)
            cached = self.get_file_by_path(path)
        
        cached['contents'][offset:offset] = list(data)
        cached['attr']['st_size'] = len(cached['contents'])
        self.api.write(path, bytes(cached['contents']))
        return len(data)

    
    def open(self, path, flags):
        print(f'open {path} {flags}')
        self.fd += 1
        return self.fd


    def get_filename_from_path(self, path):
        parts = path[1:].split('/')
        return parts[-1]

    def get_parent_from_path(self, path):
        return path[:-(len(self.get_filename_from_path(path)) + 1)]

    def append_to_parend(self, child_path, child):
        parent_path = self.get_parent_from_path(child_path)
        parent = self.get_file_by_path(parent_path)
        child['parent'] = parent
        parent['children'].append(child)

    def mkdir(self, path, mode):
        print(f'mkdir {path}')
        self.append_to_parend(path, {
            'name': self.get_filename_from_path(path),
            'type': 'DIR'
        })
        self.api.mkdir(path)
        return
        

    def rename(self, old, new):
        try:
            new_file = self.get_file_by_path(new)
            new_file['parent']['children'].remove(new_file)
            self.api.delete(new, True)
        except OSError:
            pass

        print(f'renaming {old} -> {new}')
        cached = self.get_file_by_path(old)
        self.api.rename(old, new)
        parts = new.split('/')
        cached['name'] = parts[-1]

    def rmdir(self, path):
        self.unlink(path)

    def create(self, path, mode, fi=None):
        print(f'creating {path}')
        self.append_to_parend(path, {
            'name': self.get_filename_from_path(path),
            'type': 'FILE',
            'contents': [],
        })
        self.api.write(path, bytes())
        self.fd += 1
        return self.fd

    def unlink(self, path):
        # print(f'unlinking {path}')
        cached = self.get_file_by_path(path)
        self.api.delete(path, True)
        cached['parent']['children'].remove(cached)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()