cmake_minimum_required(VERSION 3.16)
project(nova_link VERSION 0.1.0 LANGUAGES C)

option(NOVA_BUILD_TESTS "Build hardware-independent tests" ON)
option(NOVA_BUILD_TOOLS "Build offline tools and simulation" ON)
option(NOVA_BUILD_EXTENDED "Build the separate extended protocol prototype" ON)
option(NOVA_ENABLE_SANITIZERS "Enable address and undefined behavior sanitizers" OFF)

add_library(nova_link
    src/status.c src/fragment.c src/transport.c src/stream.c
    src/queue.c src/zones.c src/host.c src/scheduler.c src/radio.c)
add_library(NovaLink::nova_link ALIAS nova_link)
target_include_directories(nova_link PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_compile_features(nova_link PUBLIC c_std_99)
set_target_properties(nova_link PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)

function(nova_target target)
    set_target_properties(${target} PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror)
        if(NOVA_ENABLE_SANITIZERS)
            target_compile_options(${target} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
            target_link_options(${target} PRIVATE -fsanitize=address,undefined)
        endif()
    elseif(MSVC)
        target_compile_options(${target} PRIVATE /W4 /WX)
    endif()
endfunction()
nova_target(nova_link)
if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    # Static-library consumers also need the sanitizer runtime at final link.
    target_link_options(nova_link INTERFACE -fsanitize=address,undefined)
endif()

add_library(nova_dmx src/dmx.c)
add_library(NovaLink::nova_dmx ALIAS nova_dmx)
target_include_directories(nova_dmx PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_compile_features(nova_dmx PUBLIC c_std_99)
nova_target(nova_dmx)
if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_link_options(nova_dmx INTERFACE -fsanitize=address,undefined)
endif()

add_library(nova_multiverse src/multiverse.c)
add_library(NovaLink::nova_multiverse ALIAS nova_multiverse)
target_include_directories(nova_multiverse PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_link_libraries(nova_multiverse PUBLIC nova_dmx)
target_compile_features(nova_multiverse PUBLIC c_std_99)
nova_target(nova_multiverse)
if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_link_options(nova_multiverse INTERFACE -fsanitize=address,undefined)
endif()

# Deliberately separate test-only bytes from the installed stream engine.
if(NOVA_BUILD_TESTS OR NOVA_BUILD_TOOLS)
    add_library(nova_multiverse_synthetic src/multiverse_synthetic.c)
    target_link_libraries(nova_multiverse_synthetic PUBLIC nova_multiverse)
    nova_target(nova_multiverse_synthetic)
endif()

if(NOVA_BUILD_TOOLS)
    add_executable(nova-multiverse-sim examples/multiverse_sim.c)
    target_link_libraries(nova-multiverse-sim PRIVATE nova_multiverse_synthetic)
    nova_target(nova-multiverse-sim)
    add_executable(nova-multiverse-replay tools/multiverse_replay.c)
    target_link_libraries(nova-multiverse-replay PRIVATE nova_multiverse_synthetic)
    nova_target(nova-multiverse-replay)
    add_executable(dmx_loopback examples/dmx_loopback.c)
    target_link_libraries(dmx_loopback PRIVATE nova_dmx)
    nova_target(dmx_loopback)
    add_executable(nova-sim examples/simulation.c plugins/counter.c)
    target_include_directories(nova-sim PRIVATE plugins)
    target_link_libraries(nova-sim PRIVATE nova_link)
    nova_target(nova-sim)
    add_executable(nova-inspect tools/inspect.c)
    target_link_libraries(nova-inspect PRIVATE nova_link)
    nova_target(nova-inspect)
endif()

if(NOVA_BUILD_TESTS)
    enable_testing()
    add_executable(test_multiverse tests/test_multiverse.c)
    target_link_libraries(test_multiverse PRIVATE nova_multiverse_synthetic)
    nova_target(test_multiverse)
    add_test(NAME multiverse COMMAND test_multiverse)
    add_executable(test_dmx tests/test_dmx.c)
    target_link_libraries(test_dmx PRIVATE nova_dmx)
    nova_target(test_dmx)
    add_test(NAME dmx COMMAND test_dmx)
    find_package(Python3 COMPONENTS Interpreter QUIET)
    if(Python3_FOUND)
        add_test(NAME rf_capture COMMAND ${Python3_EXECUTABLE} -m unittest discover
            -s tests -p test_rf_capture.py WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
    endif()
    foreach(suite protocol stream_zones host radio integration)
        add_executable(test_${suite} tests/test_${suite}.c)
        target_link_libraries(test_${suite} PRIVATE nova_link)
        nova_target(test_${suite})
        add_test(NAME ${suite} COMMAND test_${suite})
    endforeach()
    if(NOVA_BUILD_TOOLS)
        add_test(NAME multiverse_simulation COMMAND nova-multiverse-sim)
        add_test(NAME dmx_loopback COMMAND dmx_loopback)
        add_test(NAME simulation COMMAND nova-sim)
        find_package(Python3 COMPONENTS Interpreter QUIET)
        if(Python3_FOUND)
            add_test(NAME multiverse_replay COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_multiverse_replay.py
                $<TARGET_FILE:nova-multiverse-sim> $<TARGET_FILE:nova-multiverse-replay>)
            add_test(NAME offline_tools COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_tools.py $<TARGET_FILE:nova-inspect>)
            add_test(NAME rf_feasibility COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_rf_feasibility.py
                ${CMAKE_CURRENT_SOURCE_DIR}/tools/rf_feasibility.py)
        endif()
    endif()
endif()

if(NOVA_BUILD_EXTENDED)
    add_subdirectory(experimental/extended)
endif()

find_package(Doxygen QUIET)
if(DOXYGEN_FOUND)
    set(DOXYGEN_PROJECT_NAME "NOVA-LINK")
    set(DOXYGEN_EXTRACT_ALL YES)
    set(DOXYGEN_WARN_AS_ERROR YES)
    set(DOXYGEN_GENERATE_LATEX NO)
    set(DOXYGEN_QUIET YES)
    set(DOXYGEN_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/api-docs")
    doxygen_add_docs(docs include/nova_link include/nova COMMENT "Generate public C API documentation")
    if(NOVA_BUILD_EXTENDED)
        add_custom_target(docs-extended
            COMMAND ${CMAKE_COMMAND} -E make_directory
                ${CMAKE_CURRENT_SOURCE_DIR}/experimental/extended/build
            COMMAND ${DOXYGEN_EXECUTABLE} Doxyfile
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/experimental/extended
            COMMENT "Generate extended prototype API documentation")
    endif()
endif()

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
configure_package_config_file(config/NovaLinkConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/NovaLinkConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/NovaLink)
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/NovaLinkConfigVersion.cmake
    VERSION ${PROJECT_VERSION} COMPATIBILITY SameMinorVersion)
install(TARGETS nova_link nova_dmx nova_multiverse EXPORT NovaLinkTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(DIRECTORY include/nova_link DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY include/nova DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    PATTERN multiverse_synthetic.h EXCLUDE)
install(EXPORT NovaLinkTargets NAMESPACE NovaLink:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/NovaLink)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/NovaLinkConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/NovaLinkConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/NovaLink)
