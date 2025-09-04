#!/usr/bin/env python3
# pylint: disable=protected-access
# pylint: disable=no-member
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import threading

from flipperzero_protobuf_py.flipperzero_protobuf.flipperzero_protobuf_compiled import flipper_pb2, storage_pb2
from flipperzero_protobuf_py.flipperzero_protobuf.flipper_proto import FlipperProto
from flipperzero_protobuf_py.flipperzero_protobuf.cli_helpers import *


class FlipperAPI():
    def __init__(self, flipper_serial) -> None:
        self.serial_port = flipper_serial
        self.proto = None
        self.mutex=threading.Lock()

    def connect(self):
        with self.mutex:
            self.proto = FlipperProto(self.serial_port)
            self.proto._in_session = True

            print("Ping result: ")
            print_hex(self.proto.rpc_system_ping())


    def _cmd_storage_list_directory(self, path):
        cmd_data = storage_pb2.ListRequest()
        cmd_data.path = path
        self.proto._rpc_send(cmd_data, 'storage_list_request')

    def _cmd_storage_stat(self, path):
        cmd_data = storage_pb2.StatRequest()
        cmd_data.path = path
        return self.proto._rpc_send_and_read_answer(cmd_data, 'storage_stat_request')

    def _cmd_storage_read(self, path):
        cmd_data = storage_pb2.ReadRequest()
        cmd_data.path = path
        self.proto._rpc_send(cmd_data, 'storage_read_request')

    def _cmd_storage_mkdir(self, path):
        cmd_data = storage_pb2.MkdirRequest()
        cmd_data.path = path
        self.proto._rpc_send(cmd_data, 'storage_mkdir_request')

    def _cmd_storage_rmdir(self, path):
        cmd_data = storage_pb2.RmdirRequest()
        cmd_data.path = path
        self.proto._rpc_send(cmd_data, 'storage_rmdir_request')

    def _cmd_storage_rename(self, old_path, new_path):
        cmd_data = storage_pb2.RenameRequest()
        cmd_data.old_path = old_path
        cmd_data.new_path = new_path
        self.proto._rpc_send(cmd_data, 'storage_rename_request')

    def _cmd_storage_delete(self, path, recursive):
        cmd_data = storage_pb2.DeleteRequest()
        cmd_data.path = path
        cmd_data.recursive = recursive
        self.proto._rpc_send(cmd_data, 'storage_delete_request')

    def _cmd_storage_write(self, path, data):
        cmd_data = storage_pb2.WriteRequest()
        cmd_data.path = path
        cmd_data.file.data = data
        self.proto._rpc_send(cmd_data, 'storage_write_request')

    def check_response_status(self, response):
        if response.command_status == flipper_pb2.CommandStatus.ERROR_STORAGE_INVALID_NAME:
            raise InvalidNameError()


    def list_directory(self, path, additional_data):
        with self.mutex:
            self._cmd_storage_list_directory(path)

            files = []

            while True:
                packet = self.proto._rpc_read_answer()
                self.check_response_status(packet)
                for file in packet.storage_list_response.file:
                    files.append({**{
                        'name': file.name,
                        'type': storage_pb2.File.FileType.Name(file.type)
                    }, **additional_data})
                if not packet.has_next:
                    break

            return files

    def stat(self, path):
        with self.mutex:
            response = self._cmd_storage_stat(path)

            if response.command_status == flipper_pb2.CommandStatus.ERROR_STORAGE_INVALID_NAME:
                raise InvalidNameError()

            response = response.storage_stat_response

            return {'size': response.file.size}

    def read_file_contents(self, path):
        with self.mutex:
            self._cmd_storage_read(path)

            contents = []

            while True:
                packet = self.proto._rpc_read_answer()
                print(packet)
                self.check_response_status(packet)
                contents.extend(packet.storage_read_response.file.data)
                if not packet.has_next:
                    break
            return {'data': contents}

    def mkdir(self, path):
        with self.mutex:
            print(f'mkdir {path}')

            self._cmd_storage_mkdir(path)

    def rmdir(self, path):
        with self.mutex:
            print(f'rmdir {path}')

            self._cmd_storage_rmdir(path)

    def rename(self, old_path, new_path):
        with self.mutex:
            self._cmd_storage_rename(old_path, new_path)

    def delete(self, path, recursive):
        with self.mutex:
            self._cmd_storage_delete(path, recursive)

    def write(self, path, data):
        with self.mutex:
            self._cmd_storage_write(path, data)

    def close(self):
        return
        # disabled because of buf in flipper_proto
        with self.mutex:
            self.proto.rpc_stop_session()

class InvalidNameError(RuntimeError):
    pass
