#!/bin/bash

make
sudo make install
sudo make reloadmodule | tail -n 5 | bat
sudo systemctl restart power-profiles-daemon

echo "Done"
