#include "common.hh"
#include "gflags/gflags.h"
static int num = 3;

DEFINE_int64(base, 1, "base");
// producer
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

    int heap_id = call_register(sd, (uint64_t) base_addr);
    printf("gid: %s, heap id: %d\n", gid, heap_id);
    res = *(int *) base_addr;

    for(int i = 0 ;i < 20; ++i) {
        sleep(1);
    }
    return 0;
}
