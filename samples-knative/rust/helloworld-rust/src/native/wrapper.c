
#include "wrapper.h"


void *create_heap(unsigned long long start_addr, unsigned long long mem_sz) {
    // (void *) 0x4ffff5a00000
    auto ptr = mmap((void *) start_addr, mem_sz,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANON, -1, 0);
    return ptr;
}