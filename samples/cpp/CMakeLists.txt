project(dmerge_samples)
ADD_DEFINITIONS(-std=c++17)
cmake_minimum_required(VERSION 3.2)
set(CMAKE_CXX_FLAGS "-O2")

SET(EXECUTABLE_OUTPUT_PATH bin) # Executable output path


set(ggflags_DIR "${CMAKE_SOURCE_DIR}/../../deps/mitosis/deps/gflags")
add_subdirectory(${CMAKE_SOURCE_DIR}/../../deps/mitosis/deps/gflags gflags_dir)


set(samples
        function merge connector full_connector
        remote_register
        )
add_executable(function cpp/function.cc)
add_executable(merge cpp/merge.cc)
add_executable(connector cpp/connector.cc)
add_executable(full_connector cpp/full-connector.cc)
add_executable(remote_register cpp/remote_register.cc)
foreach (s ${samples})
    target_link_libraries(${s} pthread gflags)
endforeach (s)


