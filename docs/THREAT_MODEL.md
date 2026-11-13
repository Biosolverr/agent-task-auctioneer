# THREAT_MODEL

Each finding: SEVERITY, ROOT CAUSE, ATTACK, CONSEQUENCE, MITIGATION, RESIDUAL, REGRESSION TEST.

**F1 CRITICAL, payout on a not-yet-final verdict.** Root: a protocol appeal can recompute an accepted transaction. Attack: withdraw after a provisional ACCEPT, then the verdict flips. Consequence: loss of escrow. Mitigation: credits are internal and recomputed with the transaction; the transfer is the last step (`withdraw`). Residual: finalization semantics of `emit_transfer` and the recomputation after a protocol appeal are NOT tested (design-level mitigation only, L2). Regression test: none for the recompute path; the accounting identity in `test_escrow.py` covers the counters only.

**F2 CRITICAL, validator checks only the format.** Root: leader output trusted. Attack: leader returns ACCEPT. Mitigation: validators recompute; mismatch -> False. Residual: leader and validators share model biases. Test: `test_validator_rejects_forged_accept`, `test_forged_leader_pin_rejected_by_validator`.

**F3 CRITICAL, stuck funds.** Root: no timer in contracts. Mitigation: every state has a permissionless exit; `force_inconclusive`; abandonment expiry. Test: `test_no_task_stays_locked_without_participant_action`, `test_stuck_*`.

**F4 MAJOR, winner abandons.** Mitigation: bond forfeited to the creator. Residual: 10% may be below the cost of a better opportunity. Test: `test_abandonment_forfeits_bond_and_refunds_budget`.

**F5 MAJOR, Sybil and self-dealing.** Root: wallet != identity. Mitigation: no reputation in selection; no gain from paying oneself; bond makes bid spam cost capital; 16-bid cap. Residual: an operator can fill the cap with its own bids and shut out others (bond-priced, not prevented). Test: `test_bid_cap`, `test_duplicate_bid_rejected`.

**F6 MAJOR, creator harvests bonds with unsatisfiable criteria.** Root: REJECT forfeits the bond to the creator. Attack: write vague or impossible criteria, win REJECT. Mitigation: criteria public and immutable before bidding; per-criterion evaluation; one appeal. Residual: honest agents must read criteria carefully; no on-chain criteria quality check. Status: NOT fully mitigated.

**F7 MAJOR, honest agent loses bond to a transient outage.** Found in self-review. Fixed (D8). Test: `test_unreachable_sources_revert_submission_and_agent_can_retry`.

**F8 MAJOR, silent failure of my own tests.** `vm.warp` takes an ISO string; integers failed inside the contract and a broad `except` hid it, so the first random-walk tests were vacuous. Fixed with anti-vacuity assertions in `test_invariants.py`.

**F9 MAJOR, double settlement/withdrawal.** Mitigation: status check and balance zeroed before transfer. Test: `test_settle_twice_rejected`, `test_withdraw_debits_before_transfer_and_cannot_repeat`.

**F10 MINOR, `accounting()` view loops over all tasks.** Fine for tests; costly on a large deployment. Not used by settlement.

**F12 CRITICAL (found in hosted Studio), value stranded by reverted payable calls.** Root: the host keeps value attached to a call that reverts; my payable methods reverted on invalid input. Attack/consequence: any mistaken `place_bid`/`appeal`/`create_task` (and any griefing call) loses the sender's funds; found as a 5 GEN surplus in `solvency()` and confirmed by a control test. Mitigation: payable methods validate first without mutating, then either act or refund the value into `claimable` (`_refund`), returning -1 / `REFUNDED: reason`. Residual: other revert paths in payable methods (unexpected exceptions) would still strand value. Verified in Studio: `solvency().surplus` was 0 after every runbook block, including all invalid-bid and invalid-appeal refunds. Regression test: `test_failed_payable_calls_never_strand_value`, `expect_refund` in the creation/auction/security tests.

**F13 MAJOR (found by probing), non-Latin and text-less evidence broke pinning consensus.** Root: the validator's overlap check used ASCII-only tokens, so a page with no 3-letter ASCII token (any Cyrillic page, small JSON) made every validator reject the leader. Consequence: agents could never submit such sources; the delivery window would expire and the bond be forfeited. Mitigation: unicode tokens; pages without usable text are pinned `ok=false` (retry or other source). Residual: scripts without word boundaries (CJK) compare as whole runs. Regression tests: `test_cyrillic_page_*`, `test_page_without_usable_text_*`.

**F14 MAJOR (accepted), value attached to non-payable calls is kept by the host.** The same host behaviour as F12 applies to any call: a leftover value in the Studio UI field on `settle`, `adjudicate` etc. strands funds, and a contract cannot refund what it never accounted for. Mitigation: operator discipline (set value 0 on non-payable calls) and `solvency().surplus` as a detector. Residual: unrecoverable by design.

**F15 MAJOR (accepted), open bids allow last-moment undercutting and bid copying.** Attack: watch the lowest bid, bid 1 wei lower just before the deadline (each bid costs a bond). Consequence: the creator pays less, honest early bidders lose; no fund loss. Mitigation: none in the MVP (commit-reveal would add a phase and a hidden-value problem). Residual: the winner is the lowest price at the deadline, as designed.

**F16 MINOR, transparency gap.** `get_task` did not expose the criteria, description, result or appeal state, so the "immutable manifest" could not be read through the contract. Fixed: full `get_task`, `get_bid`, `contract_info`.

**F17 MINOR, stuck re-evaluation cost the appellant its fee.** Fixed: on re-evaluation timeout the original verdict stands and the fee is returned. Test: `test_appeal_reevaluation_timeout_returns_the_fee`.

**F11 MAJOR (RESOLVED), Studio compatibility of the header.** The runner hash in the header comes from GenVM v0.2.16. The hosted Studio accepted it: the contract deployed and every runbook block executed (L1 proven).
