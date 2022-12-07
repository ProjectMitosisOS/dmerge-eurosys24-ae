CC=clang
CC_FLAGS=--target=wasm32-wasi -O3 -flto -Wl,--lto-O3 -nostdlib -Wl,--no-entry -Wl,--export-all
#CC_FLAGS=--target=wasm32 -O3 -flto -Wl,--lto-O3 -nostdlib -Wl,--no-entry -Wl,--export-all
FILE=add
compile:
	${CC} ${CC_FLAGS} -Wl,--global-base=$$[0] -Wl,--max-memory=$$[1024 * 1024 * 1024] -Wl,-z,stack-size=$$[1 * 1024 * 1024] -o ${FILE}.wasm ${FILE}.c

trans: compile
	wasm2wat ${FILE}.wasm -o ${FILE}.wat


clean:
	rm -rf *.wasm *.wat *.html