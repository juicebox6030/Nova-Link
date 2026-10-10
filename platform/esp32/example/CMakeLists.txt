cmake_minimum_required(VERSION 3.16)

# This is a compile/startup check for the documented silicon family. Board
# pinning and physical drivers belong to a separate deployment project.
set(IDF_TARGET "esp32s3" CACHE STRING "Nova-Link host silicon target")
if(NOT IDF_TARGET STREQUAL "esp32s3")
    message(FATAL_ERROR "This Nova-Link check targets ESP32-S3")
endif()
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/..")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(nova_link_plugin_check)
