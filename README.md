Agent Task Auctioneer

Evidence-backed research tasks, bought by reverse auction, escrowed on GenLayer, judged by validator consensus on consensus-pinned evidence.

**Status: READY WITH RISKS.** 152 Direct Mode tests pass, `genvm-lint` is clean, and a full scenario run was executed on a hosted GenLayer Studio deployment (section 11, `docs/STUDIO_RESULTS.md`). Not proven: payouts on a real network (Studio balances are simulated), fee levels, and INCONCLUSIVE produced by a model (reached only through the timeout path).

## Review deployment (GenLayer Studio, hosted)
**Contract address: `0xBB336a715550431BB5C2048A043E8Eda01dBDf03`**  Version `ata-2`  Constructor `adjudication_timeout_secs` = `600`.
Everything below can be inspected through the contract views (`get_task`, `get_bid`, `accounting`, `solvency`, `contract_info`) and in the Studio explorer for this address.

| Task id | Block | What it demonstrates |
|---|---|---|
| 0 | 1 | empty auction closed as NO_BIDS |
| 1 | 1 | creator cancel (CANCELLED_BY_CREATOR) |
| 2 | 2 | tie broken by bid order, winner abandons: bond forfeited (ABANDONED) |
| 3 | 3 | stuck adjudication: `force_inconclusive` after the timeout, INCONCLUSIVE, bond returned |
| 4 | 4 | main path, invalid bids refunded, short appeal window |
| 5 | 5 | prompt injection in the deliverable, unsatisfiable criterion: REJECT twice, agent appeal lost |
| 6 | 6 | domain allow-list, 12 submission attempts (11 reverted), agent appeal lost (this task was created with an unsatisfiable criterion by a form mistake, which produced the REJECT) |
| 7 | 6b | creator appeals an ACCEPT, appeal lost, fee to the winner |
| 8 | 7 | Cyrillic source pinned by consensus; REJECT because the pinned excerpt is navigation only (limitation L17) |

Final state: `solvency()` balance 0, liabilities 0, surplus 0; `accounting()` held 0, claimable_total 0, total_in = total_out = 117 GEN; `task_count()` = 9.

## 1. Problem
Paying an autonomous agent for web research needs someone to say "the work meets the criteria". A single evaluator is a trusted party; a mutable web page is not evidence.

## 2. Why GenLayer
The judgment needs web access and an LLM, and the result must be agreed on by independent validators and pinned in contract state. A normal contract cannot read pages; a backend with an LLM key is a centralized judge.

## 3. Mechanism
Immutable criteria and escrow -> lowest-price auction with a 10% bond -> evidence fetched and pinned by consensus at submission -> per-criterion evaluation re-run by validators -> verdict derived by code -> one appeal -> pull payout. Details: `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`.

## 4-8. Design documents
`docs/STATE_MACHINE.md`, `ECONOMIC_MODEL.md`, `EVIDENCE_MODEL.md`, `CONSENSUS_MODEL.md`, `THREAT_MODEL.md`, `SECURITY_INVARIANTS.md`, `TEST_MATRIX.md`, `KNOWN_LIMITATIONS.md`.

## 9. Local installation (Windows CMD, no Docker, no node, no API keys)
```
cd agent-task-auctioneer
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
Direct Mode downloads the GenVM release `v0.2.16` (about 200 MB) from github.com on the first run and caches it. The tests pin this version on purpose: Direct Mode's default ("latest", currently `v0.3.0-rc7`) had no downloadable archive when I tried it.

## 10. Direct Mode tests
```
python -m pytest
python scripts\demo_scenario.py
```
The first run takes a minute (archive extraction). Expected: `152 passed`. Web pages and model answers are mocked, so verdicts in these runs are **not** validator consensus.

Optional static check with the official linter (downloads the same archive):
```
pip install genvm-linter
genvm-lint check contracts\agent_task_auctioneer.py
```
Result when I ran it: lint passed (3 checks), validation passed, 19 methods (8 view, 11 write).

## 11. Hosted Studio (browser)
The step-by-step runbook that produced the review deployment is **`docs/RUNBOOK_RU.md`** (Russian, blocks 0 to 8, every field spelled out). Older outlines: `docs/STUDIO_RUNBOOK.md`, `docs/STUDIO_MASTER_PLAN.md` (superseded). Results: `docs/STUDIO_RESULTS.md`.

Facts verified in the hosted Studio (https://studio.genlayer.com/contracts):
- Constructor Inputs takes one integer, `adjudication_timeout_secs`; Deploy accepts the header runner hash.
- The **value** field of payable calls is in whole GEN (no decimals); numeric method arguments such as `price` are wei. There is no gas.
- List arguments (`criteria`, `urls`) are entered as JSON arrays; addresses as `0x...` strings.
- A call that reverts keeps any value attached to it on the contract (host behaviour), so payable methods never revert on invalid input: they return `-1` / `REFUNDED: reason` and credit the value to the sender's `claimable`.
- The Studio form remembers previous field values; check every field before sending.

Short path (happy path only):
1. Load `contracts/agent_task_auctioneer.py`, constructor `adjudication_timeout_secs` = `600`, Deploy, check `contract_info()` (`version` `ata-2`).
2. `create_task` with value `10` (GEN): description, criteria (`["Cites at least two distinct sources","Every claim in the result is supported by a cited source"]`), domains empty, min_sources `2`, bid_secs `900`, delivery_secs `604800`, appeal_secs `60`.
3. Accounts A, B, C: `place_bid(task_id, price_in_wei, note)` with value `1` (the bond is 10% of the budget).
4. After the bid window: `close_auction`; read `get_task`.
5. The winner: `submit_deliverable(task_id, result, [two public https URLs])`. This runs real validator consensus on real pages.
6. `adjudicate(task_id)` (real model consensus); read `get_task` (verdict, reason).
7. After the appeal window: `settle`; `get_claimable`, `withdraw`; check `accounting()` and `solvency()` (`surplus` must be 0).

## 12. What is proven and what is not
| Claim | Status |
|---|---|
| Contract logic, state machine, counter accounting identity under adversarial and random sequences | PROVEN in Direct Mode (152 tests) |
| Real contract balance covers all liabilities | PARTIALLY PROVEN (`solvent` true at every checked step in Studio, simulated balances) |
| Validator functions reject forged/invalid leader output | PROVEN in Direct Mode with one mocked validator; real validators accepted every honest leader output in the Studio run |
| Real multi-validator consensus on pinning and adjudication | PROVEN for ACCEPT and REJECT on the review deployment (see `docs/STUDIO_RESULTS.md`); INCONCLUSIVE only via the timeout path |
| Header/syntax valid for GenVM v0.2.16 (`genvm-lint`) | PROVEN |
| Hosted Studio deployment with this header | PROVEN (deployed and executed) |
| Real outbound payment | PARTIALLY PROVEN (works in hosted Studio with simulated balances; real network untested) |
| Fee levels and `MIN_BUDGET` | UNPROVEN (Studio has no gas) |
ing README.md…]()
