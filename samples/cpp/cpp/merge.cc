#include "common.hh"
#include "gflags/gflags.h"

DEFINE_int64(mac_id, 0, "machine id");
DEFINE_int64(heap_id, 1, "heap_id");
DEFINE_int64(base, 1, "base");

int
main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    TimerClock TC;
    int sd = sopen();
    call_pull(sd, FLAGS_heap_id, FLAGS_mac_id, true); // merge (pull)
    uint64_t addr = FLAGS_base + OFFSET;
    std::cout << "==== Now in Child ====" << std::endl;

    void *ptr = (void *) addr;

    // Fetch data (RDMA Read)
    int res = *(int *) ptr;

    std::cout << "latency:" << TC.getTimerMicroSec() << "us" << std::endl;
    std::cout << std::dec << "res:" << res << std::endl;
    return 0;
}
