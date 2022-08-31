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