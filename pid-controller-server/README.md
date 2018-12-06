# Controller simulation

For debug and development purposes this remote PID regulator simulator has been created. It is a C-written UDP server implementing the same instruction set interface so it acting as a real remote controller.

Architecture is based on 2-threaded execution:

  1. Main thread after initializing of the whole program goes to the forever loop where it constantly polling the socket for available messages. If some message (request) is arrived, it is processed by `process_request()` function, the response is preparing and transmitting to the sender. Otherwise the thread is sleeping for a small elementary duration.
  
  2. In coexistence, the second - stream thread - is starting at the program initialization time. It works only for transmitting and serves streaming purpose - constantly sends points to the socket right after the `stream_start` command was received by the main thread. The rest of the time the thread is sleeping waiting the signal to wake up.

The simulator has been tested under all 3 platforms:

  1. macOS: works both for Xcode (clang) and standalone GCC (Homebrew' GCC was used)
  2. UNIX: GCC under Ubuntu OS
  3. Windows: Ubuntu/GCC under WSL works perfectly

Simply run `make` to build and `./pid-controller-server` to start the program.

It can also be used as a reference design of how to implement the communicating path of your real device embedded firmware.
