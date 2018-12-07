Make .spec file:

    pyi-makespec main.py --onefile --name PID_controller_GUI --add-data .\img\eeprom.png;.\img ... --add-data .\defaultSettings.json;.\ --windowed --icon .\pyinstaller\win\icon.ico

Build dist:

    pyinstaller --clean --noconfirm PID_controller_GUI.spec

Notes:
    Do not use UPX, it may corrupt your executable
