#include <assert.h>
#include "../../../dmerge-user-libs/include/syscall.h"
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "../include/allocator.hh"
#include <chrono>

#define OFFSET (1024 * 1024 * 2 + 4096)
using Alloc = AllocatorMaster<73>;

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