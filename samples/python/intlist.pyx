from libc.stdio cimport FILE, fopen, fwrite, fclose
from libc.stdlib cimport malloc
from posix.fcntl cimport open, O_RDONLY
from posix.unistd cimport close, read, off_t

cdef extern from "sys/mman.h":
    void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t offset)
    enum:
        PROT_READ
        MAP_FILE
        MAP_SHARED

cdef extern from "sys/stat.h":
    cdef struct stat:
        off_t st_size
    int fstat(int fildes, stat *buf)

cdef class IntList:
    cdef int length
    cdef int* data

    def __init__(self, length):
        self.length = length
        self.data = <int*> malloc(sizeof(int) * length)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, v):
        self.data[i] = v

    def __iter__(self):
        for i in range(self.length):
            yield self.data[i]

    def __len__(self):
        return self.length

    cdef void write_handle(self, FILE* f):
        fwrite(&(self.length), sizeof(int), 1, f)
        fwrite(<void*>self.data, sizeof(int), self.length, f)

    cdef int* read_mmaped(self, int* buf):
        self.length = buf[0]
        self.data = &buf[1]
        return &buf[self.length+1]

    def __repr__(self):
        return 'IntList({0})'.format(list(self))

import random
def write_stuff(fn, int K, int N):
    cdef FILE* f = fopen(fn, 'w')
    # Write size header
    fwrite(&K, sizeof(int), 1, f)
    # Create K IntList instances of random size and content and write them
    for k in range(K):
        x = IntList(random.randrange(N/2, N))
        for i in range(len(x)):
            x[i] = random.randrange(-N, N)
        x.write_handle(f)
    fclose(f)

def read_stuff(fn):
    cdef int fd = open(fn, O_RDONLY)
    assert fd >= 0
    # Read size header
    cdef int K
    read(fd, &K, sizeof(int))
    # Get file size
    cdef stat statbuf
    fstat(fd, &statbuf)
    # Memory map file
    cdef void* buf = mmap(NULL, statbuf.st_size, PROT_READ, MAP_FILE|MAP_SHARED, fd, 0)
    buf = &(<int*>buf)[1] # skip size header
    # Read IntList objects
    cdef IntList x
    for k in range(K):
        x = IntList.__new__(IntList)
        buf = <void*> x.read_mmaped(<int*> buf)
        yield x
    close(fd)