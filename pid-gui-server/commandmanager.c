//
//  commandmanager.c
//  server
//
//  Created by Андрей Чуфырев on 18.11.2018.
//  Copyright © 2018 Андрей Чуфырев. All rights reserved.
//

#include "commandmanager.h"


//void _print_binary(unsigned char byte) {
//    printf("0b");
//    for (int i=7; i>=0; i--) {
//        if ((byte & (1<<i)) == (1<<i))
//            printf("1");
//        else
//            printf("0");
//    }
//    printf(", ");
//    printf("0x%X\n", byte);
//}

static float stream_values[2];


#define STREAM_BUF_SIZE (sizeof(char)+2*sizeof(float))
pthread_t pv_stream_thread_id;
// pthread_mutex_t sock_mutex;
static volatile bool stream_run = false;  // to prevent compiler of deleting 'while' loop in _stream_thread
// static volatile bool stream_was_run = false;

static int points_cnt = 0;

void *_stream_thread(void *data) {

    struct timespec pv_thread_delay = {
        .tv_sec = 0,        /* seconds */
        // .tv_nsec = 500000000  // 0.5 s
        //        .tv_nsec = 16666667       /* nanoseconds */  // 60 FPS
        .tv_nsec = 20000000
    };

    unsigned char stream_buf[STREAM_BUF_SIZE];
    stream_buf[0] = STREAM_PREFIX;

    double x = 0.0;
    double const dx = 0.1;

    printf("Hello from thread\n");

    while (1) {
        if (stream_run) {
            // pthread_mutex_lock(&sock_mutex);

            if (x > 2.0*M_PI)
                x = 0.0;
            stream_values[0] = (float)sin(x);  // Process Variable
            stream_values[1] = (float)cos(x);  // Controller Output
            x = x + dx;

            memcpy(&stream_buf[1], stream_values, 2*sizeof(float));

            ssize_t n = sendto(sockfd, (const void *)stream_buf, STREAM_BUF_SIZE, 0, (const struct sockaddr *)&clientaddr, clientlen);
            if (n < 0)
                error("ERROR on sendto");

            points_cnt++;

            // pthread_mutex_unlock(&sock_mutex);
            nanosleep(&pv_thread_delay, NULL);
        }
    }
}


void stream_start(void) {
    if (!stream_run) {
        stream_run = true;
        // stream_was_run = false;
    }
}

void stream_stop(void) {
    if (stream_run) {
        stream_run = false;
        // stream_was_run = true;

        printf("points: %d\n", points_cnt);
        points_cnt = 0;
    }
}


/*
 *  Sample values
 */
static float setpoint = 1238.0f;
static float kP = 19.4f;
static float kI = 8.7f;
static float kD = 1.6f;
static float err_I = 2055.0f;
static float err_P_limits[2] = {-3500.0f, 3500.0f};
static float err_I_limits[2] = {-6500.0f, 6500.0f};


int process_request(unsigned char *request_buf) {
    //int process_request(unsigned char *request_buf, unsigned char *response_buf) {

    int result = 0;

    response_t request;
    //    request_t request;
    memcpy(&request, request_buf, sizeof(char));

    //    response_t response;
    //    memcpy(&response, request_buf, sizeof(char));

    //    float values[2];
    //    memset(values, 0, 2*sizeof(float));

    //    printf("OPCODE: 0x%X\n", opcode);
    //    printf("VAR CMD: 0x%X\n", var_cmd);

    if (request.opcode == OPCODE_read) {
        printf("read: ");
        memset(&request_buf[1], 0, 2*sizeof(float));
        switch (request.var_cmd) {
            case CMD_stream_stop:
                printf("CMD_stream_stop\n");
                stream_stop();
                result = RESULT_ok;
                break;
            case CMD_stream_start:
                printf("CMD_stream_start\n");
                stream_start();
                result = RESULT_ok;
                break;

            case VAR_setpoint:
                printf("VAR_setpoint\n");
                memcpy(&request_buf[1], &setpoint, sizeof(float));
                //                values[0] = setpoint;
                result = RESULT_ok;
                break;
            case VAR_kP:
                printf("VAR_kP\n");
                memcpy(&request_buf[1], &kP, sizeof(float));
                //                values[0] = kP;
                result = RESULT_ok;
                break;
            case VAR_kI:
                printf("VAR_kI\n");
                memcpy(&request_buf[1], &kI, sizeof(float));
                //                values[0] = kI;
                result = RESULT_ok;
                break;
            case VAR_kD:
                printf("VAR_kD\n");
                memcpy(&request_buf[1], &kD, sizeof(float));
                //                values[0] = kD;
                result = RESULT_ok;
                break;
            case VAR_err_I:
                printf("VAR_err_I\n");
                memcpy(&request_buf[1], &err_I, sizeof(float));
                //                values[0] = err_I;
                result = RESULT_ok;
                break;
            case VAR_err_P_limits:
                printf("VAR_err_P_limits\n");
                memcpy(&request_buf[1], err_P_limits, 2*sizeof(float));
                //                memcpy(values, err_P_limits, 2*sizeof(float));
                result = RESULT_ok;
                break;
            case VAR_err_I_limits:
                printf("VAR_err_I_limits\n");
                memcpy(&request_buf[1], err_I_limits, 2*sizeof(float));
                //                memcpy(values, err_I_limits, 2*sizeof(float));
                result = RESULT_ok;
                break;

            case CMD_save_to_eeprom:
                printf("CMD_save_to_eeprom\n");
                result = RESULT_ok;
                break;

            default:
                printf("Unknown request\n");
                result = RESULT_error;
                break;
        }
        //        memcpy(&response_buf[1], values, 2*sizeof(float));
    }
    else {
        printf("write: ");
        //        memcpy(values, &request_buf[1], 2*sizeof(float));
        switch (request.var_cmd) {
            case VAR_setpoint:
                printf("VAR_setpoint\n");
                memcpy(&setpoint, &request_buf[1], sizeof(float));
                //                setpoint = values[0];
                result = RESULT_ok;
                break;
            case VAR_kP:
                printf("VAR_kP\n");
                memcpy(&kP, &request_buf[1], sizeof(float));
                //                kP = values[0];
                result = RESULT_ok;
                break;
            case VAR_kI:
                printf("VAR_kI\n");
                memcpy(&kI, &request_buf[1], sizeof(float));
                //                kI = values[0];
                result = RESULT_ok;
                break;
            case VAR_kD:
                printf("VAR_kD\n");
                memcpy(&kD, &request_buf[1], sizeof(float));
                //                kD = values[0];
                result = RESULT_ok;
                break;
            case VAR_err_I:
                printf("VAR_err_I\n");
                if (*(float *)&request_buf[1] == 0.0f) {
                    //                if (values[0] == 0.0f) {
                    err_I = 0.0f;
                    result = RESULT_ok;
                }
                else {
                    result = RESULT_error;
                }
                break;
            case VAR_err_P_limits:
                printf("VAR_err_P_limits\n");
                memcpy(err_P_limits, &request_buf[1], 2*sizeof(float));
                //                memcpy(err_P_limits, values, 2*sizeof(float));
                result = RESULT_ok;
                break;
            case VAR_err_I_limits:
                printf("VAR_err_I_limits\n");
                memcpy(err_I_limits, &request_buf[1], 2*sizeof(float));
                //                memcpy(err_I_limits, values, 2*sizeof(float));
                result = RESULT_ok;
                break;

            default:
                printf("Unknown request\n");
                result = RESULT_error;
                break;
        }
        memset(&request_buf[1], 0, 2*sizeof(float));
    }

    request.result = result;
    memcpy(request_buf, &request, sizeof(char));
    //    response.result = result;
    //    memcpy(response_buf, &response, sizeof(char));

    return result;
}
