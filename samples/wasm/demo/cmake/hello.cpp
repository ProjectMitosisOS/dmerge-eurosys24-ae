#include <vector>
#include <iostream>

/**
mkdir build
cd build
emcmake cmake ..
make -j
 * */
int main(int argc, char *argv[]) {
    std::vector<int> nums(10);

    for (int i = 0; i < nums.size(); ++i) {
        nums[i] = i;
        std::cout << "Get addr is "
                  << (unsigned long long) &nums[i]
                  << std::endl;
    }
    return 0;
}
