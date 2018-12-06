Make .spec file:

    pyi-makespec main.py --onefile --name PID_controller_GUI --add-data ./img/eeprom.png:./img ... --add-data ./defaultSettings.json:. --windowed --icon ./pyinstaller/mac/icon.icns

Build dist:

    pyinstaller --clean --noconfirm ./pyinstaller/mac/PID_controller_GUI.spec
