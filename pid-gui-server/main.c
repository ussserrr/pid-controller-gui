//
//  main.c
//  pid-gui-server
//
//  Created by Andrey Chufyrev on 18.11.2018.
//  Copyright © 2018 Andrey Chufyrev and authors of corresponding code. All rights reserved.
//

#include "commandmanager.h"

#include <netdb.h>
#include <sys/ioctl.h>
#include <arpa/inet.h>


#define REQUEST_RESPONSE_BUF_SIZE (sizeof(char)+2*(sizeof(float)))  // same size for both requests and responses
#define SERVER_TASK_SLEEP_TIME_MS 5
#define NO_MSG_TIMEOUT_SECONDS 15.0


int sockfd;
struct sockaddr_in clientaddr;  // client address
socklen_t clientlen;  // byte size of client's address


/*
 *  Wrapper for perror
 */
void error(char *msg) {
    perror(msg);
    exit(1);
}


int main() {

    // if (sodium_init() < 0)
    //     error("ERROR initializing libsodium");  // panic! the library couldn't be initialized, it is not safe to use

    // if (pthread_mutex_init(&sock_mutex, NULL) != 0)
    //     error("ERROR initializing mutex");

    // /*
    //  * check command line arguments
    //  * usage:
    //  *     $ <program_name> <port>
    //  */
    //
    // int main(int argc, char **argv) {
    //
    //     if (argc != 2) {
    //         fprintf(stderr, "usage: %s <port>\n", argv[0]);
    //         exit(1);
    //     }
    //
    //     int portno = atoi(argv[1]);
    //
    //     ...
    //
    int portno = 1200;  // port to listen on

    /*
     *  socket: create the parent socket
     */
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0)
        error("ERROR opening socket");

    /*
     *  setsockopt: Handy debugging trick that lets us rerun the server immediately after we kill it;
     *  otherwise we have to wait about 20 secs. Eliminates "ERROR on binding: Address already in use" error.
     */
    int optval = 1;  // flag value for setsockopt
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, (const void *)&optval, sizeof(int));

    /*
     *  build the server's Internet address
     */
    struct sockaddr_in serveraddr;  // server address
    memset((unsigned char *)&serveraddr, 0, sizeof(serveraddr));
    serveraddr.sin_family = AF_INET;
    serveraddr.sin_addr.s_addr = htonl(INADDR_ANY);
    serveraddr.sin_port = htons((unsigned short)portno);

    /*
     *  bind: associate the parent socket with a port
     */
    if (bind(sockfd, (struct sockaddr *)&serveraddr, sizeof(serveraddr)) < 0)
        error("ERROR on binding");

    clientlen = sizeof(clientaddr);  // byte size of client's address

    unsigned char buf[REQUEST_RESPONSE_BUF_SIZE];  // message buffer (both for receiving and sending)
    memset(buf, 0, REQUEST_RESPONSE_BUF_SIZE);  // explicitly reset the buffer
    // unsigned char response_buf[REQUEST_RESPONSE_BUF_SIZE];
    // memset(response_buf, 0, REQUEST_RESPONSE_BUF_SIZE);

    int err = pthread_create(&stream_thread_id, NULL, _stream_thread, NULL);
    if (err) {
        printf("%s\n", strerror(err));
        error("ERROR cannot create thread");
    }

    struct timespec server_response_delay = {
        /* seconds */      .tv_sec = 0,
        /* nanoseconds */  .tv_nsec = SERVER_TASK_SLEEP_TIME_MS * 1000000
    };

    int no_msg_cnt = 0;
    int const no_msg_cnt_warn = NO_MSG_TIMEOUT_SECONDS/(SERVER_TASK_SLEEP_TIME_MS/1000.0);
    bool is_stream_stop = false;

    
    printf("Server listening on port %d\n", portno);

    /*
     *  main loop: wait for a datagram, process it, reply
     */
    while (1) {

        if ((no_msg_cnt >= no_msg_cnt_warn) && (!is_stream_stop)) {
            printf("No incoming messages within a timeout, stop the stream\n");
            stream_stop();
            is_stream_stop = true;
        }


        int data_len = 0;
        // pthread_mutex_lock(&sock_mutex);
        ioctl(sockfd, FIONREAD, &data_len);  // check for available data in socket
        if (data_len > 0) {

            /*
             *  recvfrom: receive a UDP datagram from a client
             *  n: message byte size
             */
            ssize_t n = recvfrom(sockfd, buf, REQUEST_RESPONSE_BUF_SIZE, 0, (struct sockaddr *)&clientaddr, &clientlen);
            if (n < 0)
                error("ERROR in recvfrom");
            // printf("server received %zd bytes\n", n);

            /*
             *  gethostbyaddr: determine who sent the datagram
             *  hostp: client host info
             */
            struct hostent *hostp = gethostbyaddr((const char *)&clientaddr.sin_addr.s_addr,
                                                  sizeof(clientaddr.sin_addr.s_addr), AF_INET);
            if (hostp == NULL)
                error("ERROR on gethostbyaddr");
            char *hostaddrp = inet_ntoa(clientaddr.sin_addr);  // dotted decimal host addr string
            if (hostaddrp == NULL)
                error("ERROR on inet_ntoa");

            /*
             *  print raw received data
             */
            // printf(buf);

            process_request(buf);
            //        process_request(buf, response_buf);

            /*
             *  sendto: reply to the client
             */
            n = sendto(sockfd, (const void *)buf, REQUEST_RESPONSE_BUF_SIZE, 0, (struct sockaddr *)&clientaddr, clientlen);
            if (n < 0)
                error("ERROR in sendto");

            // pthread_mutex_unlock(&sock_mutex);
            memset(buf, 0, REQUEST_RESPONSE_BUF_SIZE);  // reset the buffer

            no_msg_cnt = 0;
            is_stream_stop = false;
        }

        // no available data
        else {
            // pthread_mutex_unlock(&sock_mutex);

            if (!is_stream_stop)
                no_msg_cnt++;

            // sleep only if there were not available data, this should allows to reply on several continuous requests
            // without any lag
            nanosleep(&server_response_delay, NULL);  // pause the main thread, then repeat
        }
    }

    return 0;
}
