cmake_minimum_required(VERSION 3.16)
project(nova_link VERSION 0.1.0 LANGUAGES C)

add_library(nova_dmx STATIC src/dmx.c)
target_include_directories(nova_dmx PUBLIC include)
target_compile_features(nova_dmx PUBLIC c_std_11)
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(nova_dmx PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(dmx_loopback examples/dmx_loopback.c)
target_link_libraries(dmx_loopback PRIVATE nova_dmx)

include(CTest)
if(BUILD_TESTING)
    add_executable(test_dmx tests/test_dmx.c)
    target_link_libraries(test_dmx PRIVATE nova_dmx)
    add_test(NAME dmx COMMAND test_dmx)
endif()
