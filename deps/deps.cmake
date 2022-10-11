cmake_minimum_required(VERSION 3.2)

include( ExternalProject )
# ./configure --with-jemalloc-prefix=je --prefix=../deps && make -j && make install
set(jemalloc_INSTALL_DIR ${CMAKE_SOURCE_DIR}/deps/jemalloc)
ExternalProject_Add(jemalloc
        SOURCE_DIR ${CMAKE_SOURCE_DIR}/deps/jemalloc
        CONFIGURE_COMMAND autoconf
        BUILD_COMMAND ./configure --with-jemalloc-prefix=je --prefix=${jemalloc_INSTALL_DIR}
        BUILD_IN_SOURCE 1
        INSTALL_COMMAND make -j12)
include_directories(./deps/jemalloc/include)