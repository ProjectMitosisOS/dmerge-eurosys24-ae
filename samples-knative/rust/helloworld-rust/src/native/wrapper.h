#pragma once

#include <stdio.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>

enum LibMITOSISCmd {
    Register = 0,
    Pull = 1,
    ConnectSession = 3,
};

typedef struct {
    unsigned int machine_id; // should not be zero!
    unsigned int nic_id; // nic idx according to gid
    const char *gid;
} connect_req_t;

void *create_heap(unsigned long long start_addr, unsigned long long mem_sz);

int sopen();

int call_register(int sd, unsigned long long peak_addr);

int call_pull(int sd);

int
call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id);