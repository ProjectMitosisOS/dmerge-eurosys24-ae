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

typedef struct {
    unsigned long long heap_base;
    unsigned int heap_hint;
} register_req_t;

typedef struct {
    unsigned int heap_hint;
    unsigned int machine_id;
} pull_req_t;

void *create_heap(unsigned long long start_addr, unsigned long long mem_sz);

int sopen();

int
call_register(int sd, unsigned long long peak_addr, unsigned int hint) ;

int
call_pull(int sd, unsigned int hint, unsigned int machine_id);

int
call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id) ;