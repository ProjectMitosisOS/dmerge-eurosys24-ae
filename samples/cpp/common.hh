#include <assert.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "../include/allocator.hh"
#include <chrono>


using Alloc = AllocatorMaster<73>;

static inline void init_heap(unsigned long long base_addr, unsigned int hint, unsigned long long mem_sz) {
    auto ptr = mmap((void *) base_addr, mem_sz * 2,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANON, -1, 0);

    Alloc::init((char *) ptr, mem_sz * 2);

    Alloc::get_thread_allocator()->alloc(mem_sz);

    int sd = sopen();
    call_register(sd, (uint64_t) base_addr, 74);

}

class TimerClock {
public:
    TimerClock() {
        update();
    }

    ~TimerClock() {
    }

    void update() {
        _start = std::chrono::high_resolution_clock::now();
    }

    double getTimerSecond() {
        return getTimerMicroSec() * 0.000001;
    }

    double getTimerMilliSec() {
        return getTimerMicroSec() * 0.001;
    }

    long long getTimerMicroSec() {
        return std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::high_resolution_clock::now() - _start).count();
    }

private:
    std::chrono::time_point<std::chrono::high_resolution_clock> _start;
};