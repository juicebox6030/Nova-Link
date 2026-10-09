cmake_minimum_required(VERSION 3.13)
project(nova_link_extended VERSION 0.1.0 LANGUAGES C)

# Host build of the portable core: unit tests, simulator, and tools.
# This prototype has a distinct API and link framing from the root SDK.

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(NL_WERROR "Treat warnings as errors" ON)
option(NL_UBSAN "Build with UBSan in trap mode (no runtime library needed)" OFF)
if(DEFINED NOVA_BUILD_TESTS)
  set(NL_BUILD_TESTS ${NOVA_BUILD_TESTS})
else()
  option(NL_BUILD_TESTS "Build unit and integration tests" ON)
endif()
if(DEFINED NOVA_BUILD_TOOLS)
  set(NL_BUILD_SIM ${NOVA_BUILD_TOOLS})
else()
  option(NL_BUILD_SIM "Build the RF simulator" ON)
endif()

if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
set(NL_WARNINGS -Wall -Wextra -Wshadow -Wpointer-arith -Wstrict-prototypes
                -Wmissing-prototypes -Wconversion -Wno-sign-conversion)
if(NL_WERROR)
  list(APPEND NL_WARNINGS -Werror)
endif()
elseif(MSVC)
  set(NL_WARNINGS /W4)
  if(NL_WERROR)
    list(APPEND NL_WARNINGS /WX)
  endif()
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

add_library(nova_link_extended STATIC ${NL_CORE_SOURCES})
target_include_directories(nova_link_extended PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
function(nl_target target)
  target_compile_options(${target} PRIVATE ${NL_WARNINGS})
  if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(${target} PRIVATE -fsanitize=address,undefined)
  endif()
endfunction()
nl_target(nova_link_extended)
if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  target_link_options(nova_link_extended INTERFACE -fsanitize=address,undefined)
endif()

if(NL_UBSAN AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-fsanitize=undefined -fsanitize-undefined-trap-on-error)
  target_compile_options(nova_link_extended PRIVATE -fsanitize=undefined
                         -fsanitize-undefined-trap-on-error)
endif()

if(NL_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

if(NL_BUILD_SIM AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/sim/CMakeLists.txt)
  add_subdirectory(sim)
endif()
