cmake_minimum_required(VERSION 3.15)
project(sample-wasm)

set(CMAKE_C_STANDARD 11)
set(CMAKE_EXECUTABLE_SUFFIX ".html")

add_executable(hello hello.cpp)

set_target_properties(hello PROPERTIES LINK_FLAGS " \
    -s WASM=1 \
    -s TOTAL_MEMORY=1GB \
    -s GLOBAL_BASE=0 \
    -s STACK_SIZE=4MB \
    -s EXIT_RUNTIME=1 \
")