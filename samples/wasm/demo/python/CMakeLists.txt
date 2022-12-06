cmake_minimum_required(VERSION 3.18)
project(python-embedding)

set(CMAKE_C_STANDARD 11)
set(CMAKE_SYSTEM_NAME normal)

if (CMAKE_SYSTEM_NAME STREQUAL "Wasm")
    set(CMAKE_EXECUTABLE_SUFFIX ".html")
endif ()

find_package(Python REQUIRED Development)
add_executable(main main.cpp)
target_link_libraries(main PRIVATE Python::Python)


if (CMAKE_SYSTEM_NAME STREQUAL "Wasm")
    set_target_properties(main PROPERTIES LINK_FLAGS " \
    -s WASM=1 \
    -s TOTAL_MEMORY=1GB \
    -s GLOBAL_BASE=0 \
    -s STACK_SIZE=4MB \
    -s EXIT_RUNTIME=1 \
")
endif ()
