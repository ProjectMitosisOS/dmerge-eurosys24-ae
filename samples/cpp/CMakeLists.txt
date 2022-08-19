project(simple_cpp_examples)
ADD_DEFINITIONS(-std=c++17)
cmake_minimum_required(VERSION 3.2)
include( ExternalProject )
set(CMAKE_CXX_FLAGS "-O2")

set(jemalloc_INSTALL_DIR ${CMAKE_SOURCE_DIR}/../../deps/jemalloc)
ExternalProject_Add(jemalloc
        SOURCE_DIR ${CMAKE_SOURCE_DIR}/../../deps/jemalloc
        CONFIGURE_COMMAND autoconf
        BUILD_COMMAND ./configure --with-jemalloc-prefix=je --prefix=${jemalloc_INSTALL_DIR}
        BUILD_IN_SOURCE 1
        INSTALL_COMMAND make -j12)
include_directories(./deps/jemalloc/include)

find_library(jemalloc_lib NAMES jemalloc PATHS ../../deps/jemalloc PATH_SUFFIXES lib
        NO_DEFAULT_PATH)

if(NOT jemalloc_lib)
    set(jemalloc_lib "")
endif()



set(samples
        function)
add_executable(function function.cc)
foreach(s ${samples})
    target_link_libraries(${s} pthread)
endforeach(s)


