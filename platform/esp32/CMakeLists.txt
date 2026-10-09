# Use this directory as an ESP-IDF component; no driver or radio configuration is applied.
set(NOVA_LINK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../..")
idf_component_register(
    SRCS
        "${NOVA_LINK_ROOT}/src/status.c"
        "${NOVA_LINK_ROOT}/src/fragment.c"
        "${NOVA_LINK_ROOT}/src/transport.c"
        "${NOVA_LINK_ROOT}/src/stream.c"
        "${NOVA_LINK_ROOT}/src/queue.c"
        "${NOVA_LINK_ROOT}/src/zones.c"
        "${NOVA_LINK_ROOT}/src/host.c"
        "${NOVA_LINK_ROOT}/src/scheduler.c"
        "${NOVA_LINK_ROOT}/src/radio.c"
    INCLUDE_DIRS "${NOVA_LINK_ROOT}/include")
target_compile_features(${COMPONENT_LIB} PUBLIC c_std_99)
