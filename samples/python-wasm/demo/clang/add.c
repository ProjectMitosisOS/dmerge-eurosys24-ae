
/**
Filename: add.c

 clang \
  --target=wasm32 \ # Target WebAssembly
  -emit-llvm \ # Emit LLVM IR (instead of host machine code)
  -c \ # Only compile, no linking just yet
  -S \ # Emit human-readable assembly rather than binary
  add.c

clang --target=wasm32 -O3 -flto -Wl,--lto-O3 -nostdlib -Wl,--no-entry -Wl,--export-all -Wl,-z,stack-size=$[8 * 1024 * 1024] -o add.wasm add.c

 */

int add(int a, int b) {
    return a*a + b;
}

int sum(int a[], int len) {
    int sum = 0;
    for(int i = 0; i < len; i++) {
        sum += a[i];
    }
    return sum;
}
