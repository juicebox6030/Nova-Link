add_library(nl_sim_core STATIC nl_sim.c)
target_include_directories(nl_sim_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(nl_sim_core PUBLIC nova_link_extended)
nl_target(nl_sim_core)

add_executable(nl_sim sim_main.c)
target_link_libraries(nl_sim PRIVATE nl_sim_core)
nl_target(nl_sim)

if(NL_BUILD_TESTS)
  add_executable(test_sim test_sim.c)
  target_link_libraries(test_sim PRIVATE nl_sim_core nl_test_support)
  nl_target(test_sim)
  add_test(NAME extended_test_sim COMMAND test_sim)

  # Regression gates on whole-network behaviour. Thresholds leave margin
  # below the values measured over several seeds when they were set
  # (single runs: broadcast_4 93.1..99.3%, p99 9..17 ms; star_8_lossy
  # 94.9..98.7%; silent 105..347 ms over 30 seeds). See docs/simulation.adoc.
  add_test(NAME extended_sim_broadcast_4
           COMMAND nl_sim --nodes 4 --duration 4 --runs 2
                   --expect-delivery 0.93 --expect-p99-ms 30)
  add_test(NAME extended_sim_star_8_lossy
           COMMAND nl_sim --preset star --nodes 8 --rate 40 --per 0.1 --duration 4
                   --runs 2 --expect-delivery 0.94)
  add_test(NAME extended_sim_silent_discovery
           COMMAND nl_sim --preset silent --nodes 8 --duration 3
                   --expect-discovery-ms 800)
endif()
