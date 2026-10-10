/**
 * @file nl_config_user.h
 * @brief Test-only config for test_isr: counting critical-section and
 * plugin hooks, built with NL_ISR_BUILD=1 (logging compiled out).
 */
#ifndef NL_CONFIG_USER_H
#define NL_CONFIG_USER_H

unsigned nl_test_crit_enter(void);
void nl_test_crit_exit(unsigned saved);
void nl_test_plugin_enter(unsigned id);
void nl_test_plugin_exit(unsigned id);

#define NL_CRITICAL_ENTER(s) ((s) = nl_test_crit_enter())
#define NL_CRITICAL_EXIT(s) nl_test_crit_exit(s)
#define NL_PLUGIN_ENTER(id) nl_test_plugin_enter(id)
#define NL_PLUGIN_EXIT(id) nl_test_plugin_exit(id)

#endif /* NL_CONFIG_USER_H */
