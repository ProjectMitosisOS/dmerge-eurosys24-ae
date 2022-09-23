#include <assert.h>
#include "../../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include "../../include/allocator.hh"
#include "include.h"
static const uint64_t heap_addr = 0x4ffff5a00000;

using Alloc = AllocatorMaster<73>;

int
main() {
    int sd = sopen();
    call_pull(sd); // merge (pull)
    void *ptr = (void *) heap_addr;

    Info res = *(Info *) ptr;

    std::cout << std::dec << "res:" << res.len << std::endl;

    std::cout << "end" << std::endl;
    return 0;
}
