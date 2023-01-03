#include "common.hh"


static void test_allocator() {
    uint64_t base_addr = BASE;
    uint64_t mem_sz = 1024 * 1024 * 512;

    base_addr += OFFSET;
    (*(int *) base_addr) = 4090;
    std::cout << std::dec << (uint64_t) (*(int *) base_addr) << "\n";

    int sd = sopen();
    int heap_id = call_register(sd, (uint64_t) base_addr, 73);
    int res = *(int *) base_addr;
    std::cout << std::dec << "res:" << res << std::endl;
}

// producer
int
main() {
    test_allocator();
    return 0;
}
