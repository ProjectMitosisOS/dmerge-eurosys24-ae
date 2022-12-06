
/**
Filename: main.c

 clang \
  --target=wasm32 \ # Target WebAssembly
  -emit-llvm \ # Emit LLVM IR (instead of host machine code)
  -c \ # Only compile, no linking just yet
  -S \ # Emit human-readable assembly rather than binary
  main.c
 */
#include <stdio.h>

int sum(int a[], int len) {
    int sum = 0;
    for (int i = 0; i < len; i++) {
        sum += a[i];
        printf("get addr of %d is 0x%lx. And %ld\n", i, (long) &a[i], (long) &a[i]);
    }
    return sum;
}

int main() {
    printf("Hello World!\n");
    int a[321];
    for (int i = 0; i < 32; ++i) a[i] = i;
    sum(a, 20);
    return 0;
}
