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
    GetMacID = 4,
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

typedef struct {
    unsigned int nic_idx;
    const char *mac_id;
} get_mac_id_req_t;

void* create_heap(unsigned long long start_addr, unsigned long long mem_sz) {
    // (void *) 0x4ffff5a00000
    void* ptr = mmap((void *) start_addr, mem_sz,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANON, -1, 0);
    unsigned long long addr = (unsigned long long) ptr;
    return ptr;
}

int
sopen() {
    return open("/dev/mitosis-syscalls", O_RDWR);
}

int
call_register(int sd, unsigned long long peak_addr, unsigned int hint) {
    register_req_t req = {.heap_base = peak_addr, .heap_hint = hint};

    int ret = ioctl(sd, Register, &req);
    if (ret == -1) {
        return -1;
    }
    return ret;
}


int
call_pull(int sd, unsigned int hint, unsigned int machine_id) {
    pull_req_t req = {.heap_hint = hint, .machine_id = machine_id};
    if (ioctl(sd, Pull, &req) == -1) {
        return -1;
    }

    return 0;
}

int
call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id) {
    connect_req_t req;
    req.gid = addr;
    req.machine_id = mac_id;
    req.nic_id = nic_id;
//    printf("[connect] get addr: %s\n", addr);
    if (ioctl(sd, ConnectSession, &req) == -1) {
        return -1;
    }

    return 0;
}
static inline int
call_get_mac_id(int sd, unsigned int nic_idx, const char* mac_id) {
    get_mac_id_req_t req;
    req.mac_id = mac_id;
    req.nic_idx = nic_idx;
    return ioctl(sd, GetMacID, &req);
}

void write_ptr(int* ptr, int val) {
    *ptr = val;
}

int read_ptr(int* ptr) {
    return *ptr;
}