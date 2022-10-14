project(simple_cpp_examples)
ADD_DEFINITIONS(-std=c++17)
cmake_minimum_required(VERSION 3.2)
set(CMAKE_CXX_FLAGS "-O2")
include(deps/deps.cmake)

find_library(jemalloc_lib NAMES jemalloc PATHS ./deps/jemalloc PATH_SUFFIXES lib
        NO_DEFAULT_PATH)
SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin) # Executable output path


if (NOT jemalloc_lib)
    set(jemalloc_lib "")
endif ()


set(samples
        function merge
        )
add_executable(function samples/cpp/function.cc)
add_executable(merge samples/cpp/merge.cc)
foreach (s ${samples})
    target_link_libraries(${s} pthread ${jemalloc_lib})
    add_dependencies(${s} jemalloc)
endforeach (s)


