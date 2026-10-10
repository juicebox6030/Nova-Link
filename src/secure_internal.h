#ifndef NOVA_LINK_SECURE_INTERNAL_H
#define NOVA_LINK_SECURE_INTERNAL_H

#include <stdbool.h>
#include "nova_link/secure.h"

/* AES-128-CCM with M=8, L=2 (RFC 3610). Encrypting writes ciphertext in place
 * and the MIC; decrypting writes plaintext in place and the expected MIC, which
 * the caller must compare in constant time. `aad_size` < 0xFF00.
 */
void nl_aes128_ccm8(const uint8_t *state, const uint8_t nonce[13], const uint8_t *aad, size_t aad_size,
                    uint8_t *data, size_t data_size, bool encrypt, uint8_t mic[8]);

#endif
