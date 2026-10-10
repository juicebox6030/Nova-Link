#ifndef NOVA_LINK_INTERNAL_H
#define NOVA_LINK_INTERNAL_H

/* Private helpers for already-validated arguments. Public entry points validate
 * once; internal hot paths use these to avoid repeated checks and struct copies.
 */
#include "nova_link/queue.h"
#include "nova_link/stream.h"

/* C99 compile-time assertion (no _Static_assert before C11). */
#define NL_STATIC_ASSERT(condition, name) typedef char nl_static_assert_##name[(condition) ? 1 : -1]

/* Ring index without division: offset < capacity, so one subtraction suffices. */
static inline size_t nl_queue_slot(const nl_queue *queue, size_t offset)
{
    size_t index = queue->head + offset;
    return index >= queue->capacity ? index - queue->capacity : index;
}

/* Borrow the head in place; NULL when empty. Valid until the next push/pop. */
static inline const nl_fragment *nl_queue_front(const nl_queue *queue)
{
    return queue->count != 0u ? &queue->storage[queue->head] : NULL;
}

/* Remove the head of a non-empty queue without copying it. */
static inline void nl_queue_drop(nl_queue *queue)
{
    queue->head = nl_queue_slot(queue, 1u);
    --queue->count;
}

/* Append a validated fragment to a non-full queue; returns its storage index. */
static inline size_t nl_queue_append(nl_queue *queue, const nl_fragment *fragment)
{
    size_t tail = nl_queue_slot(queue, queue->count);
    queue->storage[tail] = *fragment;
    ++queue->count;
    return tail;
}

nl_status nl_stream_check_valid(const nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us);
void nl_stream_commit(nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us);

#endif
