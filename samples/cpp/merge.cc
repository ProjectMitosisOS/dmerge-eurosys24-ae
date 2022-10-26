#include <assert.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "../include/allocator.hh"

using Alloc = AllocatorMaster<73>;

int
main() {
    int sd = sopen();

    call_pull(sd, 74, 0); // merge (pull)
    uint64_t addr = 0x4ffff5a00000;
    void *ptr = (void *) addr;

    int res = *(int *) ptr;

    std::cout << std::dec << "res:" << res << std::endl;

    std::cout << "end" << std::endl;
    return 0;
}
