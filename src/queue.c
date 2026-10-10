#include "internal.h"

nl_status nl_queue_init(nl_queue *queue, nl_fragment *storage, size_t capacity)
{
    /* The ring index sums two values below capacity; keep that sum in range. */
    if (queue == NULL || storage == NULL || capacity == 0u || capacity > SIZE_MAX / 2u)
        return NL_ERR_ARGUMENT;
    queue->storage = storage;
    queue->capacity = capacity;
    queue->head = 0;
    queue->count = 0;
    return NL_OK;
}

nl_status nl_queue_push(nl_queue *queue, const nl_fragment *fragment)
{
    nl_status status = nl_fragment_validate(fragment);
    if (queue == NULL) return NL_ERR_ARGUMENT;
    if (status != NL_OK) return status;
    if (queue->count == queue->capacity) return NL_ERR_FULL;
    (void)nl_queue_append(queue, fragment);
    return NL_OK;
}

nl_status nl_queue_peek(const nl_queue *queue, nl_fragment *fragment)
{
    if (queue == NULL || fragment == NULL) return NL_ERR_ARGUMENT;
    if (queue->count == 0u) return NL_ERR_EMPTY;
    *fragment = queue->storage[queue->head];
    return NL_OK;
}

nl_status nl_queue_pop(nl_queue *queue, nl_fragment *fragment)
{
    nl_status status = nl_queue_peek(queue, fragment);
    if (status != NL_OK) return status;
    nl_queue_drop(queue);
    return NL_OK;
}
