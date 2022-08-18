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
call_peak(int sd) {
    if (ioctl(sd, Peak, 0) == -1) {
        return -1;
    }

    return 0;
}
