/* Replays corpus files through a harness without libFuzzer, so GCC or any
 * other compiler can regression-test saved crashes and the seed corpus.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(int argc, char **argv)
{
    static uint8_t buffer[1u << 16];
    int i;
    for (i = 1; i < argc; ++i) {
        FILE *file = fopen(argv[i], "rb");
        size_t size;
        if (file == NULL) {
            perror(argv[i]);
            return EXIT_FAILURE;
        }
        size = fread(buffer, 1, sizeof(buffer), file);
        fclose(file);
        LLVMFuzzerTestOneInput(buffer, size);
    }
    printf("replayed %d inputs\n", argc - 1);
    return EXIT_SUCCESS;
}
