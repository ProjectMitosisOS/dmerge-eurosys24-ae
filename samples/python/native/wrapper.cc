
#include "wrapper.hh"

#include<iostream>

extern "C" {
//void *create_heap(unsigned long long start_addr, unsigned long long mem_sz) {
//    // (void *) 0x4ffff5a00000
//    auto ptr = mmap((void *) start_addr, mem_sz,
//                    PROT_READ | PROT_WRITE | PROT_EXEC,
//                    MAP_PRIVATE | MAP_ANON, -1, 0);
//    return ptr;
//}
//
//int
//sopen() {
//    return open("/dev/mitosis-syscalls", O_RDWR);
//}
//
//int
//call_register(int sd, unsigned long long peak_addr, unsigned int hint) {
//    register_req_t req = {.heap_base = peak_addr, .heap_hint = hint};
//
//    int ret = ioctl(sd, Register, &req);
//    if (ret == -1) {
//        return -1;
//    }
//    return ret;
//}
//
//
//int
//call_pull(int sd, unsigned int hint, unsigned int machine_id) {
//    pull_req_t req = {.heap_hint = hint, .machine_id = machine_id};
//    if (ioctl(sd, Pull, &req) == -1) {
//        return -1;
//    }
//
//    return 0;
//}
//
//int
//call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id) {
//    connect_req_t req;
//    req.gid = addr;
//    req.machine_id = mac_id;
//    req.nic_id = nic_id;
//
//    if (ioctl(sd, ConnectSession, &req) == -1) {
//        return -1;
//    }
//
//    return 0;
//}

extern int add(int a, int b) {
    return a + b;
}
}
