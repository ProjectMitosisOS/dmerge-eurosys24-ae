#pragma once

#include <stdio.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>

enum LibMITOSISCmd {
    Register = 0,
    Pull = 1,
};

void *create_heap(unsigned long long start_addr, unsigned long long mem_sz);

int sopen();

int call_register(int sd, unsigned long long peak_addr);

int call_pull(int sd);