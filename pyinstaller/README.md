# PyInstaller configuration

Packing into standalone application is performing via [PyInstaller](https://www.pyinstaller.org/):

 1. Pick an appropriate `.spec` file
 2. Correct user-specific options (path)
 3. Place it in the repository' root
 4. Run the command from README file

You can also generate `.spec` file by yourself using template command string from README file. It should be useful if

 - you want custom distribution options
 - new major version of PyInstaller has been released that uses incompatible format of `.spec` files.

Command-line options are more general to use for PyInstaller.
