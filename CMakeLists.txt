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

set(ggflags_DIR "${CMAKE_SOURCE_DIR}/deps/mitosis/deps/gflags")
add_subdirectory(${CMAKE_SOURCE_DIR}/deps/mitosis/deps/gflags gflags_dir)


set(samples
        function merge connector
        )
add_executable(function samples-cpp/cpp/function.cc)
add_executable(merge samples-cpp/cpp/merge.cc)
add_executable(connector samples-cpp/cpp/connector.cc)
foreach (s ${samples})
    target_link_libraries(${s} pthread ${jemalloc_lib} gflags)
    add_dependencies(${s} jemalloc)
endforeach (s)


