#include "common.hh"


// consumer
int
main() {

    TimerClock TC;
    int sd = sopen();
    call_pull(sd, 73, 0); // merge (pull)
    uint64_t addr = 0x4ffff5a00000 + OFFSET;

    void *ptr = (void *) addr;

    // Fetch data (RDMA Read)
    int res = *(int *) ptr;

    std::cout << "latency:" << TC.getTimerMicroSec() << "us" << std::endl;
    std::cout << std::dec << "res:" << res << std::endl;
    return 0;
}
