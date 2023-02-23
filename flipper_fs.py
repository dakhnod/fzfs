#!/usr/bin/env python3

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring

import errno
import stat
import time

import fuse

import flipper_api

class FlipperZeroFileSystem(fuse.Operations, fuse.LoggingMixIn):
    def __init__(self, serial_port) -> None:
        super().__init__()
        self.api = flipper_api.FlipperAPI(serial_port)
        self.api.connect()
        self.file_root = {
                'type': 'DIR'
            }
        self._fd = 0

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

        if file['type'] == 'DIR':
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
        self._fd += 1
        return self._fd

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
        self._fd += 1
        return self._fd

    def unlink(self, path):
        # print(f'unlinking {path}')
        cached = self.get_file_by_path(path)
        self.api.delete(path, True)
        cached['parent']['children'].remove(cached)
