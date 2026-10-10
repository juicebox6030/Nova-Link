cmake_minimum_required(VERSION 3.16)
project(nova_link VERSION 0.1.0 LANGUAGES C)

option(NOVA_BUILD_TESTS "Build hardware-independent tests" ON)
option(NOVA_BUILD_TOOLS "Build offline tools and simulation" ON)
option(NOVA_BUILD_EXTENDED "Build the separate extended protocol prototype" ON)
option(NOVA_ENABLE_SANITIZERS "Enable address and undefined behavior sanitizers" OFF)

add_library(nova_link
    src/status.c src/fragment.c src/transport.c src/stream.c
    src/queue.c src/zones.c src/host.c src/module.c src/scheduler.c src/radio.c
    src/spi_slave.c)
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

add_library(nova_multiverse_plugin plugins/multiverse.c)
add_library(NovaLink::nova_multiverse_plugin ALIAS nova_multiverse_plugin)
target_link_libraries(nova_multiverse_plugin PUBLIC nova_link nova_multiverse)
target_compile_features(nova_multiverse_plugin PUBLIC c_std_99)
nova_target(nova_multiverse_plugin)
if(NOVA_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_link_options(nova_multiverse_plugin INTERFACE -fsanitize=address,undefined)
endif()

add_library(nova_counter_plugin plugins/counter.c)
add_library(NovaLink::nova_counter_plugin ALIAS nova_counter_plugin)
target_link_libraries(nova_counter_plugin PUBLIC nova_link)
nova_target(nova_counter_plugin)
add_library(nova_radio_plugin plugins/radio_link.c)
add_library(NovaLink::nova_radio_plugin ALIAS nova_radio_plugin)
target_link_libraries(nova_radio_plugin PUBLIC nova_link)
nova_target(nova_radio_plugin)
add_library(nova_spi_backend plugins/spi_backend.c)
add_library(NovaLink::nova_spi_backend ALIAS nova_spi_backend)
target_link_libraries(nova_spi_backend PUBLIC nova_radio_plugin)
nova_target(nova_spi_backend)
add_library(nova_logger_plugin plugins/logger.c)
add_library(NovaLink::nova_logger_plugin ALIAS nova_logger_plugin)
target_link_libraries(nova_logger_plugin PUBLIC nova_link)
nova_target(nova_logger_plugin)
add_library(nova_config_plugin plugins/config.c)
add_library(NovaLink::nova_config_plugin ALIAS nova_config_plugin)
target_link_libraries(nova_config_plugin PUBLIC nova_link)
nova_target(nova_config_plugin)
add_library(nova_capture_plugin plugins/capture.c)
add_library(NovaLink::nova_capture_plugin ALIAS nova_capture_plugin)
target_link_libraries(nova_capture_plugin PUBLIC nova_link)
nova_target(nova_capture_plugin)
add_library(nova_plugins INTERFACE)
add_library(NovaLink::nova_plugins ALIAS nova_plugins)
target_link_libraries(nova_plugins INTERFACE
    nova_counter_plugin nova_radio_plugin nova_logger_plugin nova_multiverse_plugin
    nova_config_plugin nova_capture_plugin nova_spi_backend)

# Explicit developer support: consumers opt in without adding simulator behavior
# to the production plugin aggregate or the ESP-IDF component.
add_library(nova_plugin_conformance support/plugin_conformance.c)
add_library(NovaLink::nova_plugin_conformance ALIAS nova_plugin_conformance)
target_link_libraries(nova_plugin_conformance PUBLIC nova_link)
nova_target(nova_plugin_conformance)
add_library(nova_fault_backend src/fault_backend.c)
add_library(NovaLink::nova_fault_backend ALIAS nova_fault_backend)
target_link_libraries(nova_fault_backend PUBLIC nova_radio_plugin)
nova_target(nova_fault_backend)
add_library(nova_spi_virtual support/spi_virtual.c)
add_library(NovaLink::nova_spi_virtual ALIAS nova_spi_virtual)
target_link_libraries(nova_spi_virtual PUBLIC nova_spi_backend nova_link)
nova_target(nova_spi_virtual)

# Deliberately separate test-only bytes from the installed stream engine.
if(NOVA_BUILD_TESTS OR NOVA_BUILD_TOOLS)
    add_library(nova_multiverse_synthetic src/multiverse_synthetic.c)
    target_link_libraries(nova_multiverse_synthetic PUBLIC nova_multiverse)
    nova_target(nova_multiverse_synthetic)
endif()

if(NOVA_BUILD_TOOLS)
    add_executable(nova-spi-duplex-sim examples/spi_duplex_simulation.c)
    target_link_libraries(nova-spi-duplex-sim PRIVATE nova_spi_virtual nova_multiverse_plugin)
    nova_target(nova-spi-duplex-sim)
    add_executable(nova-spi-pair-sim examples/spi_pair_simulation.c)
    target_link_libraries(nova-spi-pair-sim PRIVATE nova_spi_virtual
        nova_counter_plugin nova_multiverse_plugin)
    nova_target(nova-spi-pair-sim)
    add_executable(nova-multiverse-sim examples/multiverse_sim.c)
    target_link_libraries(nova-multiverse-sim PRIVATE nova_multiverse_synthetic)
    nova_target(nova-multiverse-sim)
    add_executable(nova-multiverse-replay tools/multiverse_replay.c)
    target_link_libraries(nova-multiverse-replay PRIVATE nova_multiverse_synthetic)
    nova_target(nova-multiverse-replay)
    add_executable(dmx_loopback examples/dmx_loopback.c)
    target_link_libraries(dmx_loopback PRIVATE nova_dmx)
    nova_target(dmx_loopback)
    add_executable(nova-sim examples/simulation.c)
    target_link_libraries(nova-sim PRIVATE nova_counter_plugin nova_radio_plugin)
    nova_target(nova-sim)
    add_executable(nova-plugin-sim examples/plugin_simulation.c)
    target_link_libraries(nova-plugin-sim PRIVATE nova_plugins)
    nova_target(nova-plugin-sim)
    add_executable(nova-plugin-fault-sim examples/plugin_fault_simulation.c)
    target_link_libraries(nova-plugin-fault-sim PRIVATE nova_multiverse_plugin nova_fault_backend)
    nova_target(nova-plugin-fault-sim)
    add_executable(nova-config-manifest examples/config_manifest.c)
    target_link_libraries(nova-config-manifest PRIVATE nova_plugins)
    nova_target(nova-config-manifest)
    add_executable(nova-inspect tools/inspect.c)
    target_link_libraries(nova-inspect PRIVATE nova_link)
    nova_target(nova-inspect)
endif()

if(NOVA_BUILD_TESTS)
    enable_testing()
    add_executable(nova-test-spi-conformance tests/test_spi_conformance.c)
    target_link_libraries(nova-test-spi-conformance PRIVATE nova_plugin_conformance
        nova_spi_backend nova_radio_plugin nova_spi_virtual)
    nova_target(nova-test-spi-conformance)
    add_test(NAME spi_conformance COMMAND nova-test-spi-conformance)
    add_executable(nova-test-cc1352r-example tests/test_cc1352r_example.c
        platform/cc1352r/example/nova_radio_check.c)
    target_include_directories(nova-test-cc1352r-example PRIVATE
        platform/cc1352r/example)
    target_link_libraries(nova-test-cc1352r-example PRIVATE nova_link)
    nova_target(nova-test-cc1352r-example)
    add_test(NAME cc1352r_example COMMAND nova-test-cc1352r-example)
    add_executable(nova-test-spi-slave tests/test_spi_slave.c)
    target_link_libraries(nova-test-spi-slave PRIVATE nova_link)
    nova_target(nova-test-spi-slave)
    add_test(NAME spi_slave COMMAND nova-test-spi-slave)
    add_executable(nova-test-spi-virtual tests/test_spi_virtual.c)
    target_link_libraries(nova-test-spi-virtual PRIVATE nova_spi_virtual nova_counter_plugin)
    nova_target(nova-test-spi-virtual)
    add_test(NAME spi_virtual COMMAND nova-test-spi-virtual)
    add_executable(nova-test-spi-backend tests/test_spi_backend.c)
    target_link_libraries(nova-test-spi-backend PRIVATE nova_spi_backend)
    nova_target(nova-test-spi-backend)
    add_test(NAME spi_backend COMMAND nova-test-spi-backend)
    add_executable(test_capture_plugin tests/test_capture_plugin.c)
    target_link_libraries(test_capture_plugin PRIVATE nova_capture_plugin)
    nova_target(test_capture_plugin)
    add_test(NAME capture_plugin COMMAND test_capture_plugin)
    add_executable(test_plugin_conformance tests/test_plugin_conformance.c)
    target_link_libraries(test_plugin_conformance PRIVATE nova_plugin_conformance nova_plugins)
    nova_target(test_plugin_conformance)
    add_test(NAME plugin_conformance COMMAND test_plugin_conformance)
    add_executable(nova-test-plugin-conformance-negative tests/test_plugin_conformance_negative.c)
    target_link_libraries(nova-test-plugin-conformance-negative PRIVATE nova_plugin_conformance)
    nova_target(nova-test-plugin-conformance-negative)
    add_test(NAME plugin_conformance_negative COMMAND nova-test-plugin-conformance-negative)
    add_executable(test_fault_backend tests/test_fault_backend.c)
    target_link_libraries(test_fault_backend PRIVATE nova_fault_backend)
    nova_target(test_fault_backend)
    add_test(NAME fault_backend COMMAND test_fault_backend)
    add_executable(nova-test-config-plugin tests/test_config_plugin.c)
    target_link_libraries(nova-test-config-plugin PRIVATE nova_config_plugin)
    nova_target(nova-test-config-plugin)
    add_test(NAME config_plugin COMMAND nova-test-config-plugin)
    add_executable(test_multiverse_plugin tests/test_multiverse_plugin.c)
    target_link_libraries(test_multiverse_plugin PRIVATE nova_multiverse_plugin)
    nova_target(test_multiverse_plugin)
    add_test(NAME multiverse_plugin COMMAND test_multiverse_plugin)
    add_executable(test_radio_plugin tests/test_radio_plugin.c)
    target_link_libraries(test_radio_plugin PRIVATE nova_radio_plugin)
    nova_target(test_radio_plugin)
    add_test(NAME radio_plugin COMMAND test_radio_plugin)
    add_executable(test_logger_plugin tests/test_logger_plugin.c)
    target_link_libraries(test_logger_plugin PRIVATE nova_logger_plugin)
    nova_target(test_logger_plugin)
    add_test(NAME logger_plugin COMMAND test_logger_plugin)
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
        add_test(NAME plugin_scaffold COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_plugin_scaffold.py
            --sdk-build ${CMAKE_CURRENT_BINARY_DIR} --cmake ${CMAKE_COMMAND})
        add_test(NAME platform_prep COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_platform_prep.py)
        set_tests_properties(platform_prep PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
        add_test(NAME cc1352r_build_check COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_cc1352r_build_check.py)
        set_tests_properties(cc1352r_build_check PROPERTIES
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
    endif()
    foreach(suite protocol stream_zones host radio integration modules)
        add_executable(test_${suite} tests/test_${suite}.c)
        target_link_libraries(test_${suite} PRIVATE nova_link)
        nova_target(test_${suite})
        add_test(NAME ${suite} COMMAND test_${suite})
    endforeach()
    if(NOVA_BUILD_TOOLS)
        add_test(NAME spi_duplex_simulation COMMAND nova-spi-duplex-sim)
        add_test(NAME spi_pair_simulation COMMAND nova-spi-pair-sim)
        add_test(NAME multiverse_simulation COMMAND nova-multiverse-sim)
        add_test(NAME dmx_loopback COMMAND dmx_loopback)
        add_test(NAME simulation COMMAND nova-sim)
        add_test(NAME plugin_simulation COMMAND nova-plugin-sim)
        add_test(NAME plugin_fault_simulation COMMAND nova-plugin-fault-sim)
        add_test(NAME config_manifest COMMAND nova-config-manifest
            ${CMAKE_CURRENT_SOURCE_DIR}/examples/plugins.ini)
        find_package(Python3 COMPONENTS Interpreter QUIET)
        if(Python3_FOUND)
            add_test(NAME config_manifest_cli COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_config_manifest.py
                $<TARGET_FILE:nova-config-manifest>
                ${CMAKE_CURRENT_SOURCE_DIR}/examples/plugins.ini)
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
install(TARGETS nova_link nova_dmx nova_multiverse nova_multiverse_plugin
    nova_counter_plugin nova_radio_plugin nova_spi_backend nova_logger_plugin nova_config_plugin nova_capture_plugin nova_plugins
    nova_plugin_conformance nova_fault_backend nova_spi_virtual
    EXPORT NovaLinkTargets
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
install(PROGRAMS tools/new_plugin.py DESTINATION ${CMAKE_INSTALL_DATADIR}/NovaLink/tools)
install(DIRECTORY tools/plugin_templates DESTINATION ${CMAKE_INSTALL_DATADIR}/NovaLink/tools)
