TARGET=linker_test

ddyn:
	gcc -shared -o libhello.so -fPIC hello.c

dyn:
	gcc -shared -o libhello.so -fPIC hello.c -Wl,-Tdlinker.ld

# export LD_LIBRARY_PATH=/home/lfm/projects/dmerge/samples/linker-loader/libhello.so:$LD_LIBRARY_PATH

compile:
	gcc ${TARGET}.c -T linker.ld -o ${TARGET} -L. -lhello

obj:
	objdump -h ${TARGET}