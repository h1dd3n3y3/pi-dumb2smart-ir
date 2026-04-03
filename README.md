# pi-dumb2smart-ir
Python IR remote controller for the ANAVI Infrared pHAT on Raspberry Pi — record and send IR commands via an interactive terminal menu using PiIR and pigpio.

## Hardware
- Raspberry Pi Zero 2W
- [ANAVI Infrared pHAT](https://anavi.technology/)
  - TX (IR LED): GPIO 17
  - RX (IR receiver): GPIO 18

## Dependencies
- [pigpio](https://abyz.me.uk/rpi/pigpio/) — hardware-timed GPIO daemon
- [PiIR](https://github.com/ts1/PiIR) by [ts1](https://github.com/ts1) — IR record/playback library

```bash
sudo apt install python3-setuptools python3-pip -y
wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip && cd pigpio-master && make && sudo make install
cd && sudo rm -r master.zip pigpio-master

pip3 install PiIR --break-system-packages
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc && source ~/.bashrc
```

## Usage

`pigpiod` must be running before starting the script. Start it manually:

```bash
sudo pigpiod
python3 remote.py
```

To start `pigpiod` automatically on every reboot, add it to crontab (`crontab -e`):

```
@reboot /usr/bin/sudo /usr/local/bin/pigpiod
```

The interactive menu lets you:
1. Select or create a device JSON file
2. Record a key (point your remote at the pHAT and press the button)
3. Send a key
4. List all recorded keys

## Acknowledgements
This project builds on [PiIR](https://github.com/ts1/PiIR) by [ts1](https://github.com/ts1), which handles IR signal encoding, decoding, and transmission via pigpio.

