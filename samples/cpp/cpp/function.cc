#include "common.hh"


static void test_allocator() {
    uint64_t base_addr = BASE;

    base_addr += OFFSET;
    (*(int *) base_addr) = 4090;
    std::cout << std::dec << (uint64_t) (*(int *) base_addr) << "\n";

    int sd = sopen();
    int heap_id = call_register(sd, (uint64_t) base_addr);
    int res = *(int *) base_addr;
//    std::cout << "heap id:" << heap_id << std::endl;
    std::cout << std::dec << "res:" << res << std::endl;
}

// producer
int
main() {
    test_allocator();
    return 0;
}
