CC=~/wasi-sdk/bin/clang
CC_FLAGS=--target=wasm32-wasi -O3
#CC_FLAGS=--target=wasm32 -O3 -flto -Wl,--lto-O3 -nostdlib -Wl,--no-entry -Wl,--export-all
FILE=demo
compile:
	${CC} ${CC_FLAGS} -Wl,--global-base=1048576 -Wl,--max-memory=10485760  -o ${FILE}.wasm ${FILE}.c

trans: compile
	wasm2wat ${FILE}.wasm -o ${FILE}.wat


clean:
	rm -rf *.wasm *.wat *.html