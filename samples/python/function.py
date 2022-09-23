import array
import os
import mmap
import struct
from ctypes import c_int, addressof, c_uint64
import fcntl


def call_register(sd, heap_addr):
    res = fcntl.ioctl(sd, 0, c_uint64(heap_addr))
    print(res)


bar0 = 0x9ffff5a00000
mapped_memory = mmap.mmap(-1, 1024 * 1024,
                          mmap.MAP_PRIVATE, mmap.PROT_READ | mmap.PROT_WRITE, 0, bar0)
print(mapped_memory.read(16))
mapped_memory.seek(0)
mapped_memory.write(b'asd')
mapped_memory.seek(0)
print(mapped_memory.read(16))

with open("/dev/mitosis-syscalls", 'w+') as f:
    call_register(f.fileno(), bar0)
