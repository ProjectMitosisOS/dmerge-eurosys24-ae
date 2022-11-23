# distutils: language=c++

import ctypes
from libcpp.string cimport string

cdef extern from "native/wrapper.h":
    void * create_heap(unsigned long long start_addr, unsigned long long mem_sz)
    cpdef int sopen()
    cpdef int call_register(int sd, unsigned long long peak_addr, unsigned int hint)
    cpdef int call_pull(int sd, unsigned int hint, unsigned int machine_id)
    int call_connect_session(int sd, const char *addr, unsigned int mac_id, unsigned int nic_id)
    void write_ptr(int * ptr, int val)
    int read_ptr(int * ptr)


cpdef ccreate_heap(unsigned long long start_addr, unsigned long long mem_sz):
    cdef void * ptr = create_heap(start_addr, mem_sz)
    # (<int *> ptr)[0] = 1024
    #
    # cdef int result = (<int *> ptr)[0];
    # print(result)

    # TODO: Return into unsigned long long
    # return int(<int *>ptr)

cpdef int syscall_connect_session(int sd, str addr, unsigned int mac_id, unsigned int nic_id):
    cdef string caddr = addr.encode()
    return call_connect_session(sd, caddr.c_str(), mac_id, nic_id)

from libc.stdlib cimport malloc

cpdef void my_write_ptr(addr, val):
    cdef unsigned long long caddr = addr
    cdef int * ptr = <int *> caddr
    write_ptr(ptr, val)

cpdef void my_write_ptrv2(addr, val):
    cdef unsigned long long caddr = addr
    cdef int * ptr = <int *> caddr
    ptr[0] = val

cpdef int my_read_ptr(addr):
    cdef unsigned long long caddr = addr
    cdef int * ptr = <int *> caddr
    return read_ptr(ptr)

cpdef int my_read_ptrv2(addr):
    cdef unsigned long long caddr = addr
    cdef int * ptr = <int *> caddr
    return ptr[0]