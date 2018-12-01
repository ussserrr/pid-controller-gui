# TODO list

- [ ] Delimit connection-related stuff from the PID-related (e.g. `snapshots`, `reset_pid_error(err)` should be in a dedicated class). There is a rough scheme of the improved RemoteController class:
```text
RemoteController
    |
    +---- Connection(socket.socket)
    |         read()
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
    +---- Signal(QObject)
```
- [ ] Pack response, request, result etc. dictionaries into corresponding classes
