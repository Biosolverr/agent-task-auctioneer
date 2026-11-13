# TEST_MATRIX

All in `tests/direct/`, Direct Mode, real contract, mocked web and model calls. 152 tests, all passing on Python 3.12.3 with genlayer-test 0.29.2 and GenVM SDK v0.2.16.

| File | Tests | Covers |
|---|---|---|
| test_task_creation.py | 15 | valid creation, ids, below-minimum budget, zero/too many/oversized criteria, bad windows, bad domains, oversized description, nonexistent task |
| test_auction.py | 16 | bond accounting, wrong bond/price, duplicate bid, creator bid, late bid, early close, lowest wins, tie-break, double close, no bids, bid cap, cancel rules |
| test_submission.py | 8 | pinned evidence, unauthorized submit, wrong state, late submit, double submit, oversized result, abandonment, early expiry |
| test_evidence.py | 22 | 11 disallowed URL forms, allow-list and lookalike domains, duplicate/excess URLs, oversized URL, dead URL, HTML reduction, excerpt bound, unstable page, forged pin, leader error |
| test_adjudication.py | 20 | ACCEPT/REJECT/INCONCLUSIVE, 7 malformed outputs, model claiming a verdict, unknown values, prompt injection, unreachable-source retry, double adjudication, validator agree/disagree/forged/invalid, model unavailable |
| test_escrow.py | 13 | payouts per outcome, no double pay, settle twice/early, loser bonds, withdraw, rounding, `solvency()` view logic, string-address `get_claimable` |
| test_security.py | 15 | immutability, impersonation, fund redirection, terminal states, appeal rules/fees (refund semantics), stuck fallbacks, liveness, no value stranded by failed payable calls |
| test_hardening.py | 17 | manifest and bid views, `contract_info`, constructor timeout range, short-timeout `force_inconclusive`, Cyrillic pages (agree and disagree), pages without usable text, HTML entities, appeal-timeout fee refund |
| test_invariants.py | 26 | 25 seeded walks of 60 uniformly random steps (mostly shallow states; they check the accounting identity, not deep coverage) plus one 4000-step guided walk that reaches ACCEPT, REJECT, ABANDONED, NO_BIDS. INCONCLUSIVE and appeals are covered only by the deterministic tests |

Gaps: Direct Mode does not move value between accounts, so a real-balance check (`solvency()`) is proven only as view logic; no real multi-validator consensus, no real web or model, no real transfer, no storage-serialization failure test, no property-based library (seeded `random` only).

Static check: `genvm-lint check contracts/agent_task_auctioneer.py` -> lint passed (3 checks), validation passed, 19 methods (8 view, 11 write).
