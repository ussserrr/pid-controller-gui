#include "commandmanager.h"

//#include <stdio.h>
//#include <unistd.h>
//#include <stdlib.h>
//#include <string.h>
#include <netdb.h>
//#include <sys/types.h>
//#include <sys/socket.h>
#include <sys/ioctl.h>
//#include <netinet/in.h>
#include <arpa/inet.h>
//#include <pthread.h>


#define BUF_SIZE (sizeof(char)+2*(sizeof(float)))


int sockfd;
struct sockaddr_in clientaddr;  // client address
socklen_t clientlen;  // byte size of client's address

int points_cnt;
float stream_values[2];


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

    //    /*
    //     * check command line arguments
    //     * usage:
    //     *     $ <program_name> <port>
    //     */
    //
    //    int main(int argc, char **argv) {
    //
    //        if (argc != 2) {
    //            fprintf(stderr, "usage: %s <port>\n", argv[0]);
    //            exit(1);
    //        }
    //
    //        int portno = atoi(argv[1]);
    //
    //        ...
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
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR,
               (const void *)&optval, sizeof(int));

    /*
     *  build the server's Internet address
     */
    struct sockaddr_in serveraddr;  // server address
    memset((unsigned char *)&serveraddr, 0, sizeof(serveraddr));
    // bzero((char *)&serveraddr, sizeof(serveraddr));
    serveraddr.sin_family = AF_INET;
    serveraddr.sin_addr.s_addr = htonl(INADDR_ANY);
    serveraddr.sin_port = htons((unsigned short)portno);

    /*
     *  bind: associate the parent socket with a port
     */
    if (bind(sockfd, (struct sockaddr *)&serveraddr, sizeof(serveraddr)) < 0)
        error("ERROR on binding");

    clientlen = sizeof(clientaddr);  // byte size of client's address

    unsigned char buf[BUF_SIZE];  // message buffer (both for receiving and sending)
    memset(buf, 0, BUF_SIZE);  // explicitly reset the buffer
    //    unsigned char response_buf[BUF_SIZE];
    //    memset(response_buf, 0, BUF_SIZE);

    // int err = pthread_create(&pv_stream_thread_id, NULL, _stream_thread, NULL);
    // if (err) {
    //     printf("%s\n", strerror(err));
    //     error("ERROR cannot create thread");
    // }

    struct timespec server_response_delay = {
        .tv_sec = 0,        /* seconds */
        .tv_nsec = 5000000       /* nanoseconds */
    };

    printf("Server listening on port %d\n", portno);

    // volatile int msec = 0;
    // #define NO_MSG_TIMEOUT 15000  // 15 seconds
    // volatile clock_t before = clock();

    points_cnt = 0;
    int stream_divider_cnt = 0;
    unsigned char stream_buf[STREAM_BUF_SIZE];
    stream_buf[0] = STREAM_PREFIX;
    double x = 0.0;
    double const dx = 0.1;

    /*
     *  main loop: wait for a datagram, process it, reply
     */
    while (1) {

        // clock_t difference = clock() - before;
        // msec = difference * 1000 / CLOCKS_PER_SEC;
        // if (msec > NO_MSG_TIMEOUT) {
        //     printf("No incoming messages within a timeout, stop the stream\n");
        //     stream_stop();

        //     before = clock();
        //     msec = 0;

        //     // close(sockfd);
        //     // pthread_kill(pv_stream_thread_id, SIGTERM);
        //     // exit(0);
        // }


        if (stream_run) {
            if (stream_divider_cnt == 400) {
                stream_divider_cnt = 0;
                printf("stream running\n");
            }
            else if (!(stream_divider_cnt % 4)) {
//                stream_divider_cnt = 0;

                // send point
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
            }
            else
                stream_divider_cnt++;
        }


        int data_len = 0;
        // pthread_mutex_lock(&sock_mutex);
        ioctl(sockfd, FIONREAD, &data_len);  // poll for available data in socket
        if (data_len > 0) {

            /*
             *  recvfrom: receive a UDP datagram from a client
             *  n: message byte size
             */
            ssize_t n = recvfrom(sockfd, buf, BUF_SIZE, 0, (struct sockaddr *)&clientaddr, &clientlen);
            if (n < 0)
                error("ERROR in recvfrom");
            //        printf("server received %zd bytes\n", n);

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
             *  print received data
             */
            //        printf(buf);

            process_request(buf);
            //        process_request(buf, response_buf);

            /*
             *  sendto: reply to the client
             */
            n = sendto(sockfd, (const void *)buf, BUF_SIZE, 0, (struct sockaddr *)&clientaddr, clientlen);
            //        n = sendto(sockfd, (const void *)response_buf, 1 + 2*sizeof(float), 0, (struct sockaddr *)&clientaddr, clientlen);
            if (n < 0)
                error("ERROR in sendto");

            // pthread_mutex_unlock(&sock_mutex);
            memset(buf, 0, BUF_SIZE);  // reset the buffer

            // before = clock();
            // msec = 0;

            // if (stream_was_run)
            //     stream_start();
        }
        // else {
        // no available data
        // pthread_mutex_unlock(&sock_mutex);
        nanosleep(&server_response_delay, NULL);  // pause the main thread, then repeat
        // }
    }

    return 0;
}
