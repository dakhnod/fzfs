
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=line-too-long

import argparse
import logging
import os

import fuse

import flipper_fs
import flipper_serial

def main():
    parser = argparse.ArgumentParser(description='FUSE driver for flipper serial connection')
    parser.add_argument('-d', '--device', help='Serial device to connect to', dest='serial_device')
    parser.add_argument('-a', '--address', help='Flipper BLE address', dest='ble_address')
    parser.add_argument('-m', '--mount', help='Mount point to mount the FZ to', dest='mountpoint', required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    flsrl = flipper_serial.FlipperSerial()

    if not os.path.isdir(args.mountpoint) and len(os.listdir(args.mountpoint)) != 0:
        print(args.mountpoint, ': mountpoint must be an empty folder')
        return

    if args.serial_device is None and args.ble_address is None:
        args.serial_device = flsrl.discover()

    if args.serial_device is None and args.ble_address is None:
        print('either serial_device or ble_address required')
        return

    if args.serial_device is not None and args.ble_address is not None:
        print('only one of serial_device/ble_address required')
        return

    if args.ble_address is None and not os.path.exists(args.serial_device):
        print(args.serial_device,': no such file or directory')
        parser.print_usage()
        return

    try:
        serial_device = flsrl.open(serial_device=args.serial_device, ble_address=args.ble_address)
    except flipper_serial.FlipperSerialException:
        print('Failed creating serial device')
        return

    print('starting fs...')
    backend = flipper_fs.FlipperZeroFileSystem(serial_device)
    fuse.FUSE(backend, args.mountpoint, foreground=True)
    print('fuse stopped')

    backend.close()
    flsrl.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
