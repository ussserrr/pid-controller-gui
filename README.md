# maglev-client
Python-based GUI application for controlling PID regulator (see [maglev-ti-rtos](https://github.com/ussserrr/maglev-ti-rtos)).
![UNIX screenshot](/screenshots/PID_GUI_linux_gamma.png)

## Features
  - Get and set PID parameters:
    - Setpoint
    - PID algorithm output value
    - Kp, Ki and Kd coefficients
    - Limits of P & I errors
    - Resetting accumulated I error
  - Monitor controlled parameter and PID algorithm output via plots (and save them as pictures)
  - Save PID parameters to the MCU' EEPROM
  - Demo mode: activates when no network connection established

## Dependencies
  - Python 3 (tested Python 3.5+)
  - matplotlib
  - PyQt5
  - [*PyInstaller*]

## Usage
Run
```sh
$ python3 main.py
```
After loading you should see IP/port pair request and then main GUI appears.

## Packing into standalone app
Performs via [PyInstaller](https://www.pyinstaller.org/). Pick appropriate `.spec` script and run
```sh
$ pyinstaller "PID_GUI.spec"
```
As in a non-standalone case, you should run the app from terminal to be able to set IP/port and start the GUI.
Please use sources that lay under `./pyinstaller` folder. They differ only in the way to set paths to icons (see [SO](https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile) for more details).

## Notes
Some notes on app' architecture:
  - 3 modules:
    - `main`: executes general logic, renders graphics, interact with a user,
    - `mcuconn`: holds network connection to the remote MCU,
    - `miscgraphics`: contains accessory graphic (matplotlib' `Graph`, `PicButton`, etc.);
  - Version naming in order of the Greek alphabet;
  - Main window `MainWindow` inherits `QMainWindow` and includes **menu bar**, **status bar**, **toolbar** and also `FormWidget(QWidget)` containing all other elements;
  - All elements are grouped in several vertical and horizontals layouts. In turn, they are grouped together in bigger boxes. Global layout of the whole widget - `QGridLayout`;
  - Redrawing of plots is performed by setting `None` as a parent of `Graph` and repeating of drawing.

## Copyright
All rights to icons belong to icons' author from https://www.flaticon.com/. All third-party components belong to their authors.
(C) Andrey Chufyrev, 2018.
