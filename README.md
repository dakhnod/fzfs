# Flipper Zero filesystem driver

This driver allows you to mount the flipper zero over its serial connection and manage it like a regular mass storage.

## Installation

```
git clone --recursive --depth 1 git@github.com:dakhnod/fzfs.git
cd fzfs
python3 -m venv venv
. venv/bin/activate
pip install protobuf
pip install fusepy
pip install pyserial
```

## Usage

The script takes two arguments, the serial port and the mount point

```
venv/bin/python3 fzfs.py /dev/ttyACM0 /home/user/flipper-zero
```

Then you should be able to access your flipper files through file browser of the console in the mountpoint.