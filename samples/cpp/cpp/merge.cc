#include "common.hh"
#include "gflags/gflags.h"

DEFINE_int64(mac_id, 0, "machine id");

int
main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    TimerClock TC;
    int sd = sopen();
    call_pull(sd, 73, FLAGS_mac_id); // merge (pull)
    uint64_t addr = 0x4ffff5a00000 + OFFSET;

    void *ptr = (void *) addr;

    // Fetch data (RDMA Read)
    int res = *(int *) ptr;

    std::cout << "latency:" << TC.getTimerMicroSec() << "us" << std::endl;
    std::cout << std::dec << "res:" << res << std::endl;
    return 0;
}
