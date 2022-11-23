#include <iostream>
#include <string>
#include <cstdlib>
#include <vector>
#include <stdio.h>

class Test {
public:


    double _calculate(int a, int b);
};


double Test::_calculate(int a, int b) {
    double res = a * b;
    std::cout << "res: " << res << std::endl;
    return res;
}

extern "C" {
Test *test_new() {
    return new Test();
}

double my_calculate(Test *t, int a, int b) {
    return t->_calculate(a, b);
}
}