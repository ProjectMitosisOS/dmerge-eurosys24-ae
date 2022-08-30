#include <assert.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include "include/allocator.hh"

using Alloc = AllocatorMaster<73>;

static void test_merge_apply() {
    int sd = sopen();

    call_apply(sd);
}

int
main() {
    test_merge_apply();
    uint64_t addr = 0x4ffff5a00000;
    void *ptr = (void *) addr;

    int res = *(int *) ptr;

    std::cout << "res:" << res << std::endl;

    std::cout << "end" << std::endl;
    return 0;
}
