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
call_register(int sd, unsigned long long peak_addr, unsigned int hint = 0) {
    register_req_t req = {.heap_base = peak_addr, .heap_hint = hint};

    int ret = ioctl(sd, Register, &req);
    if (ret == -1) {
        return -1;
    }
    return ret;
}


static inline int
call_pull(int sd, unsigned int hint, unsigned int machine_id) {
    pull_req_t req = {.heap_hint = hint, .machine_id = machine_id};
    if (ioctl(sd, Pull, &req) == -1) {
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