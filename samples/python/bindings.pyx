# distutils: language=c++

import ctypes
from libcpp.string cimport string

cdef extern from "native/wrapper.h":
    void * create_heap(unsigned long long start_addr, unsigned long long mem_sz)
    cpdef int sopen()
    cpdef int call_register(int sd, unsigned long long peak_addr, unsigned int hint)
    cpdef int call_pull(int sd, unsigned int hint, unsigned int machine_id)
    int call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id)


cpdef ccreate_heap(unsigned long long start_addr, unsigned long long mem_sz):
    cdef void * ptr = create_heap(start_addr, mem_sz)
    (<int *> ptr)[0] = 1024

    cdef int result = (<int *> ptr)[0];
    print(result)

    # TODO: Return into unsigned long long
    # return int(<int *>ptr)

cpdef int syscall_connect_session(int sd, str addr, unsigned int mac_id, unsigned int nic_id):
    cdef string caddr = addr.encode()
    return call_connect_session(sd, caddr.c_str(), mac_id, nic_id)

cpdef void test_mem():
    cdef void * ptr = <void *> 0xffffffffffffff5a00000
    # (<int *> ptr)[0] = 102400
    cdef int result = 0;

    for i in range(20):
        result = (<int *> ptr)[i]
        print("result[%d] of child %d" % (i, result))
