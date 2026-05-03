#!/bin/bash
set -e

sudo apt install python3-setuptools python3-pip -y

wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip && cd pigpio-master && make && sudo make install
cd && sudo rm -r master.zip pigpio-master

pip3 install PiIR --break-system-packages
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc && source ~/.bashrc

