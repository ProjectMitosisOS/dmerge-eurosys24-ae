#include "common.hh"

static void test_allocator() {
    uint64_t ptr = 0x4ffff5a00000;
    init_heap(ptr, 73, 1024 * 1024 * 512);
    (*(int *) ptr) = 4096;
    std::cout << std::dec << (uint64_t) (*(int *) ptr) << "\n";

    int res = *(int *) ptr;
    std::cout << std::dec << "res:" << res << std::endl;
}

int
main() {
    test_allocator();
    return 0;
}
