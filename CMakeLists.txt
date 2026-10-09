cmake_minimum_required(VERSION 3.13)
project(nova_link VERSION 0.1.0 LANGUAGES C)

# Host build of the portable core: unit tests, simulator, and tools.
# Firmware builds will live in platform/esp32 (ESP-IDF component) and
# platform/cc1352r; neither exists yet.

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(NL_WERROR "Treat warnings as errors" ON)
option(NL_UBSAN "Build with UBSan in trap mode (no runtime library needed)" OFF)
option(NL_BUILD_TESTS "Build unit and integration tests" ON)
option(NL_BUILD_SIM "Build the RF simulator" ON)

set(NL_WARNINGS -Wall -Wextra -Wshadow -Wpointer-arith -Wstrict-prototypes
                -Wmissing-prototypes -Wconversion -Wno-sign-conversion)
if(NL_WERROR)
  list(APPEND NL_WARNINGS -Werror)
endif()

set(NL_CORE_SOURCES
  src/nl_common.c
  src/nl_fragment.c
  src/nl_link.c
  src/nl_stream_tracker.c
  src/nl_meta.c
  src/nl_zone.c
  src/nl_segment.c
  src/nl_radio.c
  src/nl_host.c
  src/nl_spi_link.c
  src/nl_ini.c
  src/nl_config_file.c
)

add_library(nova_link STATIC ${NL_CORE_SOURCES})
target_include_directories(nova_link PUBLIC include)
target_compile_options(nova_link PRIVATE ${NL_WARNINGS})

if(NL_UBSAN)
  add_compile_options(-fsanitize=undefined -fsanitize-undefined-trap-on-error)
  target_compile_options(nova_link PRIVATE -fsanitize=undefined
                         -fsanitize-undefined-trap-on-error)
endif()

if(NL_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

if(NL_BUILD_SIM AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/sim/CMakeLists.txt)
  add_subdirectory(sim)
endif()
