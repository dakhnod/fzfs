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


import flipper_serial

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
    flsrl = flipper_serial.FlipperSerial()

    if len(os.listdir(mountpoint)) != 0:
        print('mountpoint must be an empty folder')
        return

    if args.serial_device is None:
        args.serial_device = flsrl.discover()

    if args.serial_device is None and args.ble_address is None:
        print('either serial_device or ble_address required')
        return

    if args.serial_device is not None and args.ble_address is not None:
        print('only one of serial_device/ble_address required')
        return

    if not os.path.exists(args.serial_device):
        print(args.serial_device,': no such file or directory')
        parser.print_usage()
        return

    fuse_started = True
    # fuse_thread = threading.Thread(target=fuse.FUSE, kwargs={'operations': backend, 'mountpoint': mountpoint, 'foreground': True})
    def fuse_start():
        fuse.FUSE(backend, mountpoint, foreground=True)

    print('starting fs...')
    fuse_start()
    print('fuse stopped')

    flsrl.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()