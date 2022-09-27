#include <stdio.h>
#include <sys/mman.h>

void *create_heap(unsigned long long start_addr, unsigned long long mem_sz);