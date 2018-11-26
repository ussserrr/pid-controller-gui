all:
		gcc-8 main.c commandmanager.c -o pid-gui-server -D _POSIX_C_SOURCE=200809L -Wall -std=c18 -lsodium -lpthread -lm

clean:
		rm pid-gui-server
