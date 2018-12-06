//
//  commandmanager.h
//  pid-controller-server
//
//  Created by Andrey Chufyrev on 18.11.2018.
//  Copyright © 2018 Andrey Chufyrev. All rights reserved.
//

#ifndef commandmanager_h
#define commandmanager_h


#include <stdio.h>
#include <stdlib.h>
#include <string.h>  // for memset()
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <math.h>

// #include "sodium.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846264338328
#endif


extern int sockfd;
extern struct sockaddr_in clientaddr;  // client address
extern socklen_t clientlen;  // byte size of client's address

// extern pthread_mutex_t sock_mutex;
extern pthread_t stream_thread_id;


enum {
    OPCODE_read,
    OPCODE_write
};

enum {
    VAR_setpoint = 0b0100,

    VAR_kP = 0b0101,
    VAR_kI = 0b0110,
    VAR_kD = 0b0111,

    VAR_err_I = 0b1000,

    VAR_err_P_limits = 0b1001,
    VAR_err_I_limits = 0b1010,

    // special
    CMD_stream_start = 0b0001,
    CMD_stream_stop = 0b0000,

    CMD_save_to_eeprom = 0b1011
};

enum {
    RESULT_ok,
    RESULT_error
};

#define STREAM_PREFIX 0b00000001


typedef struct request {
    unsigned char _reserved: 3;
    unsigned char var_cmd : 4;
    unsigned char opcode : 1;
} request_t;

typedef struct response {
    unsigned char _reserved: 2;
    unsigned char result : 1;
    unsigned char var_cmd : 4;
    unsigned char opcode : 1;
} response_t;


// void _print_bin_hex(unsigned char byte);

void error(char *msg);

void *_stream_thread(void *data);
void stream_start(void);
void stream_stop(void);

int process_request(unsigned char *request_buf);
// int process_request(unsigned char *request_buf, unsigned char *response_buf);


#endif /* commandmanager_h */
