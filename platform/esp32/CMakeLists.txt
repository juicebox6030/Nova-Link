# Use this directory as an ESP-IDF component; no driver or radio configuration is applied.
# Developer conformance/fault support and the synthetic test codec are excluded.
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
        "${NOVA_LINK_ROOT}/src/module.c"
        "${NOVA_LINK_ROOT}/src/scheduler.c"
        "${NOVA_LINK_ROOT}/src/radio.c"
        "${NOVA_LINK_ROOT}/src/dmx.c"
        "${NOVA_LINK_ROOT}/src/multiverse.c"
        "${NOVA_LINK_ROOT}/plugins/multiverse.c"
        "${NOVA_LINK_ROOT}/plugins/counter.c"
        "${NOVA_LINK_ROOT}/plugins/radio_link.c"
        "${NOVA_LINK_ROOT}/plugins/logger.c"
        "${NOVA_LINK_ROOT}/plugins/config.c"
        "${NOVA_LINK_ROOT}/plugins/capture.c"
    INCLUDE_DIRS "${NOVA_LINK_ROOT}/include")
target_compile_features(${COMPONENT_LIB} PUBLIC c_std_99)
