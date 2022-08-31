import ctypes
import os
import mmap

if __name__ == '__main__':
    fd = open
    buf = mmap.mmap(-1, 4096, mmap.MAP_PRIVATE | mmap.MAP_ANON,
                    mmap.PROT_WRITE | mmap.PROT_READ)
    # int_pointer = ctypes.c_int.from_buffer(buf)
    with mmap.mmap(-1, 20) as mm:
        int_pointer = ctypes.c_int.from_buffer(mm)
        # print(int_pointer)
        mm.write(b"Hello Worlllld")
        mm.read(4096)
