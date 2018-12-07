# PID controller GUI
![screenshot](/screenshots/pid-controller-gui.gif)

## Features
  - Get and set PID parameters:
    - Setpoint
    - kP, kI and kD coefficients
    - Limits of proportional & integral components errors
    - Reset accumulated integral error
  - Monitor process variable and controller output through live graphs
  - Save PID parameters to the controller' non-volatile memory
  - Demo mode: activates when no network connection established

## Overview
The application is supposed to connects to some kind of bare-metal MCU or OS-based controller that uses a proportional-integral-derivative algorithm as a core to drive some parameter in physical system. PID is a generic efficient-proven method for such tasks, find more about it in topic resources.

It can be used as a general tool to help:
  - Setup and adjust the PID regulator for the first time
  - Monitor its stability during a long operation
  - Diagnose and find issues

Main advantage of the dedicated interface is the ability to establish a connection of any type while not changing the behavior of other logic. For example, current active UDP/IP stack can be replaced by a serial UART protocol and so on. The application does not contain any hard-coded specific definitions that allows to assign them by an end-user.

## Architecture
Besides modular structure the app also applies multithreaded approach to split resources on different tasks. For example, in communication protocol (described in [INSTRUCTIONSET](/INSTRUCTIONSET)) 2 types of messages are defined: 'normal' and stream. Normal variables/commands are delivering by demand, using request/response semantics. In contrast, stream messages are constantly pouring from the controller so the client should plot them onto graph. Such scene is perfectly lays on the concept of dedicated input listening thread that concurrently runs alongside the main thread and redirect incoming messages according to their type. It is implemented through `multiprocessing` API (processes and pipes).

For detailed description on particular things please refer to in-code documentation.

## Dependencies
  - Python 3
  - PyQt5
  - PyQtGraph
  - qdarkstyle (provides dark theme)
  - *[optional]* PyInstaller (provides packing into bundle)

## Usage
Run
```sh
$ python3 main.py
```

## Packing into standalone app
It is possible to bundle the application into a standalone executable using [PyInstaller](https://www.pyinstaller.org/). See respective README in [pyinstaller](/pyinstaller) folder.
