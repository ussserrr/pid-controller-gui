# PyInstaller configuration
Packing into standalone app performs via [PyInstaller](https://www.pyinstaller.org/). Pick appropriate `.spec` script and run
```sh
$ pyinstaller "PID_GUI.spec"
```
Please, prefer these sources, to be sure that all icons will be packed properly. They differ only in the way to set paths to icons (see [SO](https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile) for more details).