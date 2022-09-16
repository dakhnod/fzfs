from audioop import add
from concurrent.futures import thread
from sqlite3 import connect
import bleak
import serial
import asyncio
import threading
import time

class BLESerial(serial.Serial):
    def __init__(self, address: str, read_characteristic: str, write_characteristic: str, read_timeout=1):
        self.address = address
        self.read_characteristic = read_characteristic
        self.write_characteristic = write_characteristic
        self.client = None
        self.read_buffer = []
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.connect_condition = threading.Condition()
        self.write_condition = threading.Condition()
        self.read_condition = threading.Condition()
        self.read_timeout = read_timeout
        self.exception = None

    def start(self, disconnect_handler):
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self.connect(60, disconnect_handler), self.loop)
        with self.connect_condition:
            self.connect_condition.wait()

    def stop(self):
        asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)
        with self.connect_condition:
            self.connect_condition.wait(20)
        with self.connect_condition:
            self.connect_condition.notify()
        with self.read_condition:
            self.read_condition.notify()
        with self.write_condition:
            self.write_condition.notify()
        self.loop.stop()

    async def disconnect(self):
        await self.client.disconnect()
        with self.connect_condition:
            self.connect_condition.notify()

    async def connect(self, timeout, disconnect_handler=None):
        self.client = bleak.BleakClient(self.address, addr_type='random')
        self.client.set_disconnected_callback(disconnect_handler)
        connected = False
        for i in range(10):
            try:
                print(f'connect attempt {i + 1}/10')
                result = await self.client.connect(timeout)
                connected = True
                break
            except bleak.BleakError as e:
                pass


        if not connected:
            raise f'Could not connect to {self.address}'

        await self.client.start_notify(self.read_characteristic, self.on_serial_data)

        with self.connect_condition:
            self.connect_condition.notify()

    def on_serial_data(self, size, data):
        # print(f'received {list(data)}')
        self.read_buffer.extend(list(data))
        with self.read_condition:
            self.read_condition.notify()

    def read(self, size: int):
        # print(f'reading {size}, available {len(self.read_buffer)}')
        if len(self.read_buffer) < size:
            with self.read_condition:
                self.read_condition.wait(self.read_timeout)
        if not self.client.is_connected:
            raise Exception('Device disconnected')
        data = self.read_buffer[:size]
        self.read_buffer = self.read_buffer[size:]

        return bytes(data)

    async def write_char(self, char, data):
        try:
            result = await self.client.write_gatt_char(char, data)
        except Exception as e:
            print(e)
        with self.write_condition:
            self.write_condition.notify()

    def write(self, data):
        if not self.client.is_connected:
            raise Exception('Device disconnected')
        # print(f'writing {list(data)}')
        asyncio.run_coroutine_threadsafe(self.write_char(self.write_characteristic, data), self.loop)
        with self.write_condition:
            self.write_condition.wait(5)
        if not self.client.is_connected:
            raise Exception('Device disconnected')
