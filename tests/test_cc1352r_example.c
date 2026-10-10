#include "test.h"

extern volatile nl_status nova_cc1352r_check_status;
nl_status nova_cc1352r_run_check(void);
void *mainThread(void *argument);

int main(void)
{
    STATUS(nova_cc1352r_run_check(), NL_OK);
    CHECK(mainThread(NULL) == NULL);
    CHECK(nova_cc1352r_check_status == NL_OK);
    CHECK(mainThread(NULL) == NULL);
    CHECK(nova_cc1352r_check_status == NL_OK);
    return EXIT_SUCCESS;
}
