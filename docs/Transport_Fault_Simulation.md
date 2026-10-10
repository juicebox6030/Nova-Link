# Transport faults without hardware

`nova-plugin-fault-sim` exercises the compiled module manifests, radio-link
transport, native frame serialization, FIFO radio queues, and the Multiverse
DMX plugin together. Its checks remain enabled in Release builds. Run it after
building the repository:

```sh
./build/nova-plugin-fault-sim
ctest --test-dir build -R '^plugin_fault_simulation$' --output-on-failure
```

Its adapter is also available as the optional installed developer target
`NovaLink::nova_fault_backend`, with the public header
[`nova_link/fault_backend.h`](../include/nova_link/fault_backend.h). It is separate
from `NovaLink::nova_plugins` and is excluded from the ESP-IDF component. The
backend owns bounded native FIFO queues in caller-provided memory and performs
no I/O. New tests can use it directly instead of copying this simulation.

```c
nl_fault_options options;
nl_fault_backend backend;
nl_fault_adapter binding;
nl_radio_link transport;
nl_fault_transfer transfer;
/* Check each return value in application code. */
nl_fault_profile_options(NL_FAULT_DELAYED, &options);
nl_fault_backend_init(&backend, &options);
nl_fault_adapter_init(&binding, &backend, 2);
nl_radio_link_config config = nl_fault_adapter_link_config(&binding);
nl_radio_link_init(&transport, &config);
nl_fault_transfer_init(&transfer, options.transfer_delay_us);
/* Register nl_radio_link_module(&transport) through the normal manifest. */
```

Drive transfers only after the entire manifest starts successfully. In each
logical event, advance both backend clocks with `nl_fault_backend_set_time`,
poll the sender host, call `nl_fault_transfer_step(sender, receiver, transfer,
now_us)`, then poll the receiver host. A transfer's first call freezes the TX
head and serialized bytes; a later call attempts completion. This remains true
for zero-delay transfers. The function returns `BUSY` during preparation,
delay or disconnect, `FULL` during receive queue congestion, `EMPTY` when the
current sender window has no queued fragment, and `OK` on completion. It never
dispatches host RX itself. With multiple active zones, normal native scheduler
windows select the queue; each zone retains FIFO order. Receiver native
duplicate/stale/access rejection completes the transfer and increments
`transfer.rejected`, without dispatching that fragment.

The presets select repeatable initial conditions; the calling event loop selects
production, reconnect, invalidation and restart events:

| Profile | Transfer delay | Receipt commit delay | Initial condition |
| --- | --- | --- | --- |
| `NL_FAULT_CLEAN` | 0 | 0 | Connected |
| `NL_FAULT_DELAYED` | 400 | 900 | Connected |
| `NL_FAULT_DISCONNECTED` | 0 | 0 | Offline until explicitly connected |
| `NL_FAULT_CONGESTED` | 400 | 4000 | Produce faster than receipt commitment to fill queues |
| `NL_FAULT_COMMIT_RETRY` | 0 | 0 | First three ready commit attempts return BUSY |

All preset times are logical microseconds. `nl_fault_backend_set_connected` and
`nl_fault_backend_fail_commits` alter explicit events without clearing owned
work. Monotonic clocks reject backward steps, and delay arithmetic rejects
overflow. `backend.stats` distinguishes accepted/rejected PUSH, retained
receipts, successful/retried commits, invalidations, stale commit attempts,
startup rollback cancellations and lifecycle counts. Transfer counters report
completion, FIFO congestion retries and receiver native rejection.

Generated transport plugins use `nl_fault_adapter`, which exposes direct
send/start/stop/can-stop/poll callbacks without attaching another transport to
the host. It retains a settled response across failed commits and provides
`nl_radio_link_stats`, including delivered versus abandoned receipts. Both the
direct adapter and ordinary radio-link prevent a second dispatch after a
successful receive while committing the receipt fails.
Each direct adapter belongs to one provider lifecycle and records successful
backend acquisition. A different adapter's failed startup cannot stop or cancel
the first adapter's work. The raw `nl_fault_backend_link_config` callback context
is the backend itself: exactly one radio-link provider may use it, and no direct
adapter may share that backend concurrently. Use separate backend storage for
independent radio-link instances. The recommended
`nl_fault_adapter_link_config` factory also gives ordinary radio-link modules
this acquisition guard: initialize distinct binding storage for each lifecycle,
then build its framed configuration. A failed competing provider startup leaves
the active provider's queues and receipts intact. An adapter's direct callbacks
and framed binding cannot serve two provider lifecycles concurrently.

For explicit receipt invalidation, call `nl_fault_backend_invalidate_receipt`.
It removes only the currently held RX head. The transport's next commit sees
`STALE`, abandons its cached receipt, and can pull a replacement. A later
receipt cannot be removed by that old token, and a previously delivered
receipt is not dispatched a second time. This event may discard application
data; it is an intentional fault, not a normal acknowledgement.

Ordinary module shutdown returns `BUSY` for queued work, retained receipts, or
incoming/outgoing transfers. Stop the producer and drain before retrying.
Startup rollback bypasses the veto and cancels queued native TX/RX ownership;
this is why cross-backend transfers must begin only after successful manifest
startup. `nl_fault_backend_restart` requires a stopped, drained backend and
resets its native scheduler/dedup tracker while preserving logical time and
the monotonically allocated receipt token. Old receipts remain stale across
this explicit restart. Reset the host native origin tracker and bind any
application session separately when sequence numbers restart. Reinitializing
storage with `nl_fault_backend_init` begins a new lifetime and requires all old
owners/callbacks to have finished; it does not provide cross-lifetime safety.

The adapter uses deterministic logical time: 100-microsecond event steps,
400-microsecond transfer completion delay, 900-microsecond receipt commit delay,
and two receive receipt attempts per host poll. These are test inputs, not
measured SPI, RF, or device timings. The application payload is NLM1; this does
not establish proprietary Multiverse interoperability.

The simulation checks these failure and recovery paths:

| Scenario | Required behavior |
| --- | --- |
| Delayed transfer completion | Accepting a PUSH owns its TX queue entry locally. The original head and serialized transfer bytes stay identical until receiver queue admission succeeds. |
| Receiver disconnect during a delivered receipt | The settled response and token survive repeated failed commits. No second receive dispatch occurs. The next accepted TX entry stays owned while its completion is blocked. |
| Sender disconnect with a pending update | Failed PUSH requests leave TX queue contents and acceptance counters unchanged. Reconnect retries the retained model update. |
| Producer congestion | 400 newer snapshots arrive while transfers and commits lag. TX/RX queues reach their fixed limits of 8/16, then return FULL instead of growing. The in-flight FIFO head stays owned and is retried. |
| Latest-state recovery | The model coalesces submissions while preserving frozen updates. After draining outstanding work, an explicit FULL produces exactly the final 512 desired levels. Intermediate submission count need not equal completed frame count. |
| Shutdown with outstanding work | Manifest shutdown stops the dependent application, then returns BUSY for the transport. Its attachment and in-flight queue remain valid. A later drain permits shutdown to finish. |
| Explicit sender restart | Old TX, RX, and receipt ownership drains first. The receiver resets shared native origin tracking separately, explicitly binds model session 43, and acquires exact levels from model/native sequence zero. |
| Old receipt completion after sender restart | An old receipt from the same still-active receiver radio lifetime returns STALE and cannot remove the new receipt head. |

Every event checks bounded queue occupancy and the invariant that dispatched
native receipts equal committed receipts plus at most one settled pending
receipt. Retried commits compare the exact retained response bytes and token.
The deterministic baseline before restart reports 100 FIFO congestion retries,
800 delayed receipt retries, and 11 complete DMX updates. Native queue acceptance,
simulated transfer completion, and receive receipt dispatch totals match once
all work drains.

This adapter deliberately retains work across a temporary disconnect. A real
backend may instead invalidate receipts or cancel device operations, but must
preserve the documented ownership contract and establish when cancellation has
finished before replacing contexts. The receiver radio itself is not restarted
here: its receipt tokens remain valid only for that radio lifetime. A real
driver must prevent callbacks from an earlier backend lifetime from touching
newly initialized storage; this simulation does not assert cross-lifetime token
safety or physical completion guarantees.
