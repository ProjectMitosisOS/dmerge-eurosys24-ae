#include <assert.h>
#include "../../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include "../../include/allocator.hh"
#include "include.h"

using Alloc = AllocatorMaster<73>;


/**
 * Init the heap with heap start virtual addr and heap size
 *
 * @param heap_start: Virtual heap start address
 * @param heap_sz: Heap size in Byte
 * @return: Heap start pointer
 * */
static void *prepare_heap(uint64_t heap_start, uint64_t heap_sz) {
    auto ptr = mmap((void *) heap_start, heap_sz,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_SHARED | MAP_ANON, -1, 0);
    Alloc::init((char *) ptr, heap_sz);

    return ptr;
}


int main() {
    auto heap_ptr = prepare_heap(0x4ffff5a00000, 1024 * 1024 * 1024);
    for (int i = 0; i < 6; ++i) {
        char *tmp = (char *) (Alloc::get_thread_allocator()->alloc(4096));
        (*(int *) tmp) = 1024 * (i + 2);
    }
    int sd = sopen();
    call_register(sd, (uint64_t) heap_ptr);


    // TODO: Call mapper function
    {
        (*(Info *) heap_ptr) = Info{.type=3, .len=31};
        auto res = *(Info *) heap_ptr;
        std::cout << std::dec << "res:" << res.len << std::endl;
    }
}
