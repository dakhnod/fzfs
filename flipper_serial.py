#!/usr/bin/env python3

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=line-too-long


import serial
import serial.tools.list_ports
import serial_ble

class FlipperSerial():
    _flipperusb = "USB VID:PID=0483:5740"
    _read_characteristic = '19ed82ae-ed21-4c9d-4145-228e61fe0000'
    _write_characteristic = '19ed82ae-ed21-4c9d-4145-228e62fe0000'
    _is_cli = True

    def discover(self):
        ports = serial.tools.list_ports.comports()
        for check_port in ports:
            if self._flipperusb in check_port.hwid:
                print("Found: ", check_port.description, "(",check_port.device,")")
                return check_port.device
        return None

    def open(self, **resource):
        for key, value in resource.items():
            if key == "serial_device" and value is not None:
                rsc = self._create_physical_serial(value)
            if key == "ble_address" and value is not None:
                rsc =  self._create_ble_serial(value)

        if rsc is None:
            raise FlipperSerialException
        return rsc

    def close(self):
        try:
            self._serial_device.stop()
            print('stopped bluetooth')
        except AttributeError:
            pass

    def _create_physical_serial(self, file):
        resource = serial.Serial(file, timeout=1)
        if self._is_cli:
            resource.read_until(b'>: ')
            resource.write(b"start_rpc_session\r")
            resource.read_until(b'\n')
            
        return resource

    def _create_ble_serial(self, address):
        bluetooth = serial_ble.BLESerial(address, self._read_characteristic, self._write_characteristic)
        print('connecting...')
        bluetooth.start(None)
        print('connected')

        return bluetooth

class FlipperSerialException(Exception):
    pass
