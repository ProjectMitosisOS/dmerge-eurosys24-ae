#include "common.hh"
#include "gflags/gflags.h"
DEFINE_int64(base, 0x4ffff5a00000, "base");
// producer
// BASE_HEX=4ffff5a00000 TOTAL_SZ_HEX=20000000 LD_PRELOAD=/home/lfm/libmalloc_wrapper.so ./bin/remote_register
int
main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);
    uint64_t base_addr = FLAGS_base;

    base_addr += OFFSET;
    (*(int *) base_addr) = 4090;
    std::cout << std::dec << (uint64_t) (*(int *) base_addr) << "\n";

    int sd = sopen();
    char gid[49];
    size_t machine_id[1];
    int res = call_get_mac_id(sd,0, gid, machine_id);
    int heap_id = call_register_remote(sd, (uint64_t) base_addr, 0);
    printf("gid: %s, heap id: %d\n", gid, heap_id);
    return 0;
}
