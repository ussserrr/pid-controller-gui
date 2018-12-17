# pid-controller-gui

- [ ] Delimit connection-related stuff from the PID-related (e.g. `snapshots`, `reset_pid_error(err)` should be in a dedicated class). There is a rough scheme of the improved RemoteController class:
```text
RemoteController
    |
    +---- Connection(socket.socket)    allows easily switch interfaces
    |         read()                   (e.g. from Ethernet to serial)
    |         write()
    |         check()
    |
    +---- PID
    |         snapshots
    |         take_snapshot()
    |         restore_snapshot(snapshot)
    |
    |
    +---- Stream
    |
    +---- Signal(QObject)    no more present in the class (zero external
                             dependencies, only Python library)
```
- [ ] Pack response, request, result etc. into corresponding classes, not dictionaries
- [ ] Add logging to easily trace the execution flow (several verbosity levels)
- [ ] Apply settings on-the-fly (not requiring a reboot)
- [ ] Make QT signals propagate from children to parent and vice versa (more ease and transparent code)
- [ ] Get rid of entangled logic of handling connection and its breaks
- [ ] Display the lag (in points) of plots instead of bullet mark


# pid-controller-server

- [ ] Store the connection information on the first communication to eliminate the need in determination of the client's IP on every incoming request (reset them after specified inactivity timeout) (maybe this is closer to TCP nature...)
