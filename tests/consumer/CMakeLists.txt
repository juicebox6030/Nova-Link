cmake_minimum_required(VERSION 3.16)
project(nova_consumer LANGUAGES C)
find_package(NovaLink 0.1 CONFIG REQUIRED)
add_executable(consumer main.c)
target_link_libraries(consumer PRIVATE NovaLink::nova_plugins
    NovaLink::nova_plugin_conformance NovaLink::nova_fault_backend
    NovaLink::nova_spi_virtual)
