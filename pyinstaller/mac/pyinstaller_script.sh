#!/usr/bin/env bash

pyinstaller main.py --clean --noconfirm --onefile --name PID_controller_GUI --add-data ./img/eeprom.png:./img --add-data ./defaultSettings.json:. --windowed --icon ./pyinstaller/mac/icon.icns