Make .spec file:

    pyi-makespec main.py --onefile --name PID_controller_GUI --add-data ./img/eeprom.png:./img ... --add-data ./defaultSettings.json:.

Build dist:

    pyinstaller --clean --noconfirm PID_controller_GUI.spec
