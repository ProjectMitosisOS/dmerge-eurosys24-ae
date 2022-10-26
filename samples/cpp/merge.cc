#include "common.hh"

int
main() {

    TimerClock TC;
    uint64_t _ptr = 0x600005a00000;
    init_heap(0x600005a00000, 80, 1024 * 1024 * 512);
    int sd = sopen();

    call_pull(sd, 73, 0); // merge (pull)
    uint64_t addr = 0x4ffff5a00000;
    void *ptr = (void *) addr;

    int res = *(int *) ptr;

    std::cout << "latency:" << TC.getTimerMicroSec() << "us" << std::endl;
    std::cout << std::dec << "res:" << res << std::endl;
    return 0;
}
