#include <vector>
#include <iostream>

/**
mkdir build
cd build
emcmake cmake ..
make -j
 * */
static inline std::chrono::time_point<std::chrono::system_clock> get_cur_tick() {
    return std::chrono::system_clock::now();
}

static inline double elapsed(std::chrono::time_point<std::chrono::system_clock> start) {
    std::chrono::duration<double> elapsed_duration = std::chrono::system_clock::now() - start;
    return elapsed_duration.count();
}

int main(int argc, char *argv[]) {
    auto start = get_cur_tick();

    std::vector<int> nums(2000);

    for (int i = 0; i < nums.size(); ++i) {
        nums[i] = i * i;
        std::cout << "Get addr is "
                  << (unsigned long long) &nums[i]
                  << std::endl;
    }

    double tick_passed_us = elapsed(start) * 1000000;
    std::cout << "elapsed time:" << tick_passed_us << std::endl;
    return 0;
}
