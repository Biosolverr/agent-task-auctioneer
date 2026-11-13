# ARCHITECTURE

One Intelligent Contract: `contracts/agent_task_auctioneer.py`. No backend, no frontend, no external contracts.

```
create_task(escrow) -> place_bid(bond) -> close_auction -> submit_deliverable [consensus round 1: pin evidence]
  -> adjudicate [consensus round 2: evaluate] -> (appeal -> adjudicate) -> settle -> withdraw
```

Differentiated mechanism: evidence is fixed by validator consensus when it is submitted, and the judgment (and any appeal) runs on that fixed snapshot against immutable per-criterion rules, with the verdict derived by deterministic code. An auction, an escrow and an LLM are each ordinary; the combination that makes disputes reproducible is the claim. It is not a claim of objective truth.

## Constructor and views
`__init__(adjudication_timeout_secs)` (60 s to 30 d) sets how long `force_inconclusive` waits; a short value lets a reviewer exercise the stuck-adjudication path on the same deployed address. Views: `get_task` (full manifest, deliverable, pins, appeal state), `get_bid`, `get_claimable(str)`, `get_last_rejection(str)`, `accounting`, `solvency`, `contract_info`, `task_count`.

## Storage
`tasks: DynArray[Task]`, `bids/pins: TreeMap[str, ...]` keyed `task_id:index`, `claimable: TreeMap[Address, u256]`, counters `total_in`, `total_out`, `claimable_total`. All money is `u256` wei; arithmetic is done on Python ints and cast back.

## GenLayer operations
| Function | Context | Nondet input | Leader | Validator | Equivalence | Deterministic change after consensus | Failure |
|---|---|---|---|---|---|---|---|
| `submit_deliverable` | `run_nondet_unsafe` | `gl.nondet.web.get` per URL | fetches, reduces HTML to visible text, returns `[{url, ok, excerpt<=1200}]` | re-fetches every URL; `ok` must match; at least 60% of the leader excerpt's word tokens must occur in its own text; excerpt must be empty when not ok | custom | store pins, status SUBMITTED | no agreement or fewer than `min_sources` reachable: transaction reverts, no state change |
| `adjudicate` | `run_nondet_unsafe` | `gl.nondet.exec_prompt(..., response_format="json")` on stored pins (no web access) | returns `{verdict, passes[], reason}` derived from per-criterion flags | recomputes the same function independently, compares `verdict` only (reason text may differ) | custom | store verdict, reason, appeal deadline | malformed model output -> INCONCLUSIVE; model unavailable -> revert; no agreement -> protocol rotation/appeal; 7-day timeout -> `force_inconclusive` |

Rules followed: storage is read into plain Python values before the nondet block; nothing is written inside it; closures capture only plain data.

## Authority table
| Operation | Caller | Preconditions | Replay |
|---|---|---|---|
| create_task | anyone | value >= MIN_BUDGET, bounded inputs; invalid input returns -1 and refunds the value to claimable (no revert) | new task each call |
| place_bid | anyone but creator | OPEN, before deadline, exact bond, one bid per address, <=16 bids | duplicate reverts |
| close_auction | anyone | OPEN, after deadline | second call reverts |
| cancel_task | creator | OPEN and zero bids | second call reverts |
| expire_assignment | anyone | ASSIGNED, after delivery deadline | terminal |
| submit_deliverable | winner | ASSIGNED, before deadline | second call reverts |
| adjudicate | anyone | SUBMITTED or APPEALED | second call reverts |
| force_inconclusive | anyone | 7 days stuck | leaves stuck state |
| appeal | losing party | ADJUDICATED, window open, fee == bond | status moves to APPEALED |
| settle | anyone | ADJUDICATED, window closed | status SETTLED, second call reverts |
| withdraw | any balance holder | claimable > 0 | balance zeroed first |
[ARCHITECTURE.md](https://github.com/user-attachments/files/34786487/ARCHITECTURE.md)
