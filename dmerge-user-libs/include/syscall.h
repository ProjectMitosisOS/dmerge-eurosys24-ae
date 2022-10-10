#pragma once

#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>

#include "./common.h"

static inline int
sopen() {
    return open("/dev/mitosis-syscalls", O_RDWR);
}

static inline int
call_register(int sd, unsigned long long peak_addr) {
    if (ioctl(sd, Register, peak_addr) == -1) {
        return -1;
    }

    return 0;
}


static inline int
call_pull(int sd) {
    if (ioctl(sd, Pull, 0) == -1) {
        return -1;
    }

    return 0;
}

static inline int
call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id) {
    connect_req_t req;
    req.gid = addr;
    req.machine_id = mac_id;
    req.nic_id = nic_id;

    if (ioctl(sd, ConnectSession, &req) == -1) {
        return -1;
    }

    return 0;
}