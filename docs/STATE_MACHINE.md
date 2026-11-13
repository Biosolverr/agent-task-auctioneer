# STATE_MACHINE

Statuses: OPEN(0) ASSIGNED(1) SUBMITTED(2) ADJUDICATED(3) APPEALED(4) SETTLED(5, terminal) CANCELLED(6, terminal).

| From | Call | To | Who | Money effect |
|---|---|---|---|---|
| (none) | create_task | OPEN | anyone | budget escrowed |
| OPEN | place_bid | OPEN | non-creator | bond escrowed |
| OPEN | cancel_task (no bids) | CANCELLED | creator | budget -> creator claimable |
| OPEN | close_auction, no bids | CANCELLED (NO_BIDS) | anyone | budget -> creator claimable |
| OPEN | close_auction, bids | ASSIGNED | anyone | loser bonds -> claimable |
| ASSIGNED | expire_assignment | SETTLED (ABANDONED) | anyone | budget + bond -> creator |
| ASSIGNED | submit_deliverable | SUBMITTED | winner | none |
| SUBMITTED | adjudicate | ADJUDICATED | anyone | none |
| SUBMITTED | force_inconclusive (7d) | ADJUDICATED (INCONCLUSIVE) | anyone | none |
| ADJUDICATED | appeal | APPEALED | losing party | fee == bond escrowed |
| APPEALED | adjudicate | ADJUDICATED (final) | anyone | none |
| APPEALED | force_inconclusive (7d) | ADJUDICATED (original verdict stands) | anyone | none |
| ADJUDICATED | settle (window closed or final) | SETTLED | anyone | payout credits (ECONOMIC_MODEL) |

Every other (state, call) pair reverts (tested in `test_security.py::test_terminal_task_cannot_reopen` and the auction/submission tests). Liveness: each non-terminal state has a permissionless exit (`test_no_task_stays_locked_without_participant_action`).
