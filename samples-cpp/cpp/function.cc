#include "common.hh"


static void test_allocator() {
    uint64_t base_addr = 0x4ffff5a00000;
    uint64_t mem_sz = 1024 * 1024 * 512;

    auto ptr = mmap((void *) base_addr, mem_sz,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANON, -1, 0);

    Alloc::init((char *) ptr, mem_sz);

    // Force touch all
    for (int i = 0; i < mem_sz; ++i) {
        *(char *) (base_addr + i) = '\0';
    }
    auto cur_ptr = Alloc::get_thread_allocator()->alloc(1024 * 1024 * 128);

    base_addr += OFFSET;
    (*(int *) base_addr) = 4096;
    std::cout << std::dec << (uint64_t) (*(int *) base_addr) << "\n";

    int sd = sopen();
    call_register(sd, (uint64_t) base_addr, 73);

    int res = *(int *) base_addr;
    std::cout << std::dec << "res:" << res << std::endl;
    (*(int *) base_addr) = 2048;

}

// producer
int
main() {
    test_allocator();
    return 0;
}
