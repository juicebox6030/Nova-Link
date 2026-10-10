add_library(nl_test_support STATIC nl_test.c)
target_include_directories(nl_test_support PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(nl_test_support PUBLIC nova_link_extended)
nl_target(nl_test_support)

set(NL_TESTS
  test_fragment
  test_link
  test_tracker
  test_meta
  test_zone
  test_segment
  test_radio
  test_host
  test_spi_link
  test_config
)

# test_config loads the shipped example config/nova_link.ini.
set_source_files_properties(test_config.c PROPERTIES
  COMPILE_DEFINITIONS "NL_SOURCE_DIR=\"${PROJECT_SOURCE_DIR}\"")

foreach(t ${NL_TESTS})
  add_executable(extended_${t} ${t}.c)
  target_link_libraries(extended_${t} PRIVATE nl_test_support)
  nl_target(extended_${t})
  add_test(NAME extended_${t} COMMAND extended_${t})
endforeach()

# ---- ISR build: counting critical-section/plugin hooks, logging compiled out
set(NL_ISR_SOURCES)
foreach(s ${NL_CORE_SOURCES})
  list(APPEND NL_ISR_SOURCES ${PROJECT_SOURCE_DIR}/${s})
endforeach()
add_library(nova_link_extended_isr STATIC ${NL_ISR_SOURCES})
target_include_directories(nova_link_extended_isr PUBLIC
  ${PROJECT_SOURCE_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR}/isr_config)
target_compile_definitions(nova_link_extended_isr PUBLIC NL_HAVE_CONFIG_USER NL_ISR_BUILD=1)
nl_target(nova_link_extended_isr)

add_executable(extended_test_isr test_isr.c nl_test.c)
target_include_directories(extended_test_isr PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(extended_test_isr PRIVATE nova_link_extended_isr)
nl_target(extended_test_isr)
add_test(NAME extended_test_isr COMMAND extended_test_isr)

# ---- Shared test vectors for the Python tools (tools/) -------------------
# gen_vectors prints JSON vectors computed by the C core. Regenerate with:
#   build/tests/gen_vectors --out tests/vectors
add_executable(gen_vectors gen_vectors.c)
target_link_libraries(gen_vectors PRIVATE nova_link_extended)
nl_target(gen_vectors)

# Fails when tests/vectors/*.json no longer match the C implementation.
add_test(NAME extended_vectors_up_to_date
         COMMAND gen_vectors --check ${CMAKE_CURRENT_SOURCE_DIR}/vectors)

find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME extended_python_tools
           COMMAND ${Python3_EXECUTABLE} -m unittest discover -s tools/tests -t tools
           WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
endif()
