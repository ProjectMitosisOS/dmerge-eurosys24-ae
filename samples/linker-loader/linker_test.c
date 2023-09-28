#include <stdio.h>
#include <unistd.h>

extern void hello();

int main() {
    hello();
    sleep(10);

    return 0;
}