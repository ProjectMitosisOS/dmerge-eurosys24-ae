CC=emcc
CC_FLAGS=-O3 -flto -Wl,--lto-O3
FILE=main
compile:
	${CC} ${CC_FLAGS} -s TOTAL_MEMORY=1GB -s STACK_SIZE=4MB -s GLOBAL_BASE=0 -o ${FILE}.js ${FILE}.c
	#${CC} ${CC_FLAGS} -s TOTAL_MEMORY=1GB -s STACK_SIZE=4MB -s GLOBAL_BASE=4096 -o ${FILE}.js ${FILE}.c

trans: compile
	wasm2wat ${FILE}.wasm -o ${FILE}.wat


clean:
	rm -rf *.wasm *.wat *.html *.js