# Flipper Zero filesystem driver

This driver allows you to mount the flipper zero over its serial connection and manage it like a regular mass storage.

## Installation

```
git clone --recursive https://github.com/dakhnod/fzfs.git
cd fzfs
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Connect via USB Serial

The script takes two arguments, the serial port and the mount point

```
venv/bin/python3 fzfs.py -d /dev/ttyACM0 -m /home/user/flipper-zero
```

Then you should be able to access your flipper files through file browser of the console in the mountpoint.

## Connect via BLE Serial

First, you need to pair your flipper with your computer. This process varies, but a good starting point is:
```
bluetoothctl
agent on
pair your_flipper_mac_address
disconnect your_flipper_mac_address
```

This should ask you for a confirmation code and pair your device.
After that, ensure that your Flipper is disconnected from your computer.

Then, you can run

```
venv/bin/python3 fzfs.py -a "your_flipper_mac_address" -m /home/user/flipper-zero
```

## Disclaimer

This software is still work in progress and may have errors despite my best efforts, so use with caution.
