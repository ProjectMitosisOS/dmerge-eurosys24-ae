#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>


int nums[32];

int main(int argc, char **argv) {
    void *ptr = malloc(1024);
    printf("hello world %lld\n", (unsigned long long) ptr);
    printf("Static array in %lld\n", (unsigned long long) nums);
    int num = *(int*)200;
    printf("data is %d\n", num);

//    sleep(30);

}