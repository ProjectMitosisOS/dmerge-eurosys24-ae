#include <assert.h>
#include "../../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include "../../include/allocator.hh"
#include "include.h"

using Alloc = AllocatorMaster<73>;

int
main() {
    int sd = sopen();
    call_pull(sd); // merge (pull)
    uint64_t addr = 0x4ffff5a00000;
    void *ptr = (void *) addr;

    Info res = *(Info *) ptr;

    std::cout << std::dec << "res:" << res.len << std::endl;

    std::cout << "end" << std::endl;
    return 0;
}
