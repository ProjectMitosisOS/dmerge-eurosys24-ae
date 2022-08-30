#include <assert.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include "include/allocator.hh"

using Alloc = AllocatorMaster<73>;

static void test_km(uint64_t peak_addr) {
    int sd = sopen();
    assert(sd != 0);

    call_peak(sd, peak_addr);
}

static void test_allocator() {

    // mmap
    uint64_t mem_sz = 1024 * 1024 * 1024;
    auto ptr = mmap((void*)0x4ffff5a00000, mem_sz,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_SHARED | MAP_ANON, -1, 0);

    std::cout << std::hex << (uint64_t) ptr << "\n";

    (*(int*) ptr) = 1024;
    Alloc::init((char *) ptr, mem_sz);

    for (int i = 0; i < 6; ++i) {
        char *tmp = (char *) (Alloc::get_thread_allocator()->alloc(4096));

        std::cout << "[" << i << "]" << std::endl << std::hex << (uint64_t) ptr << "\n" <<
                  (uint64_t) tmp << std::endl;
//        Alloc::get_thread_allocator()->dealloc(tmp);
    }

    test_km((uint64_t) ptr);
}

int
main() {
    test_allocator();
    return 0;
}
