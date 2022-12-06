cmake_minimum_required(VERSION 3.5)
project(python-embedding)

set(CMAKE_C_STANDARD 11)
set(CMAKE_SYSTEM_NAME notWasm)

if (CMAKE_SYSTEM_NAME STREQUAL "Wasm")
    set(CMAKE_EXECUTABLE_SUFFIX ".html")
    set(DEMO_FUNC_LIBS faasm c-printscan-long-double)
    set(PYTHON_LIBRARIES ${CMAKE_SOURCE_DIR}/lib/libpython3.8.a)
    set(PYTHON_INCLUDE_DIRS ${CMAKE_SOURCE_DIR}/lib/python3.8)
else ()
    find_package(Python REQUIRED Development)
endif ()

add_executable(main main.cpp)


if (CMAKE_SYSTEM_NAME STREQUAL "Wasm")
    set_target_properties(main PROPERTIES LINK_FLAGS " \
    -s WASM=1 \
    -s TOTAL_MEMORY=1GB \
    -s GLOBAL_BASE=0 \
    -s STACK_SIZE=4MB \
    -s EXIT_RUNTIME=1 \
")
#    target_link_libraries(main emscripten c-printscan-long-double util)
    target_link_libraries(main ${PYTHON_LIBRARIES})
    target_include_directories(main PUBLIC ${PYTHON_INCLUDE_DIRS})
else ()
    target_link_libraries(main PRIVATE Python::Python)
endif ()
