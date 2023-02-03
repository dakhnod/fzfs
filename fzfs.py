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
import serial.tools.list_ports
import sys

flipperusbid = "USB VID:PID=0483:5740"

def autodiscover():
    ports = serial.tools.list_ports.comports()
    for check_port in ports:
        if flipperusbid in check_port.hwid:
            print("Found: ", check_port.description, "(",check_port.device,")")
            return check_port.device
    return None

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

    if args.serial_device is None:
        args.serial_device = autodiscover()

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

    return bluetooth

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()