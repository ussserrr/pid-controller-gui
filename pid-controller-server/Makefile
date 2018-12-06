all:
		gcc-8 main.c commandmanager.c -o pid-controller-server -D _POSIX_C_SOURCE=200809L -Wall -std=c18 -lsodium -lpthread -lm -Ofast

clean:
		rm pid-controller-server
