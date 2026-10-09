#ifndef NOVA_LINK_QUEUE_H
#define NOVA_LINK_QUEUE_H

#include "nova_link/fragment.h"

/** @file queue.h Bounded FIFO with caller-owned storage. Not internally synchronized. */
typedef struct {
    nl_fragment *storage;
    size_t capacity;
    size_t head;
    size_t count;
} nl_queue;

nl_status nl_queue_init(nl_queue *queue, nl_fragment *storage, size_t capacity);
nl_status nl_queue_push(nl_queue *queue, const nl_fragment *fragment);
nl_status nl_queue_peek(const nl_queue *queue, nl_fragment *fragment);
nl_status nl_queue_pop(nl_queue *queue, nl_fragment *fragment);

#endif
