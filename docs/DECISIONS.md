# DECISIONS

Format: QUESTION / OPTIONS / DECISION / REASON / TRADEOFF / RISK / MITIGATION / PROOF METHOD.

## D1 Task scope
- QUESTION: universal agent marketplace or one task class?
- OPTIONS: (a) any task, (b) evidence-backed web research only.
- DECISION: (b). REASON: only research output can be judged from a bounded set of public pages plus written criteria. TRADEOFF: much narrower product. RISK: reviewers read it as a toy. MITIGATION: the narrowness is stated, not hidden. PROOF: `create_task` requires 1..3 source URLs, criteria are per-item checkable.

## D2 Winner selection
- OPTIONS: (a) lowest price, (b) price+reputation, (c) creator picks.
- DECISION: (a) lowest price, ties to the earliest bid. REASON: wallets are not identities, so any reputation can be farmed by one operator with many wallets; creator choice reintroduces a trusted party. TRADEOFF: price does not prove capability. RISK: race to the bottom, winner abandons. MITIGATION: every bidder posts a 10% bond (D3). PROOF: `test_lowest_price_wins_and_losers_refunded`, `test_tie_broken_by_earliest_bid`.

## D3 Bid bond instead of staking or reputation
- DECISION: each bid carries a bond of 10% of the budget. Losers get it back at closure, the winner gets it back on ACCEPT or INCONCLUSIVE, loses it to the creator on REJECT or abandonment. REASON: smallest mechanism that prices abandonment and Sybil bid spam. TRADEOFF: capital lockup. RISK: creator writes unsatisfiable criteria to harvest bonds (THREAT F6). MITIGATION: criteria are visible and immutable before bidding; one appeal. PROOF: `test_abandonment_forfeits_bond_and_refunds_budget`, `test_reject_refunds_creator_and_forfeits_bond`.

## D4 Evidence is pinned by consensus at submission
- OPTIONS: (a) fetch live pages during adjudication, (b) fetch and pin when the agent submits, (c) agent pastes text.
- DECISION: (b). REASON: (a) judges a mutable page and makes appeals non-reproducible; (c) is unverifiable. Pinning makes validators agree on what each URL said at submission time and later evaluation (including the appeal) uses that fixed excerpt. TRADEOFF: one extra consensus round and on-chain storage (<=1200 chars per URL). RISK: pinning proves what a page said, not that it is true. PROOF: `test_stable_page_validator_agrees`, `test_unstable_page_validator_disagrees`, `test_forged_leader_pin_rejected_by_validator`.

## D5 The model never chooses the verdict
- DECISION: the model returns one pass/fail/unknown flag per criterion; the contract derives the verdict (any false -> REJECT, all true -> ACCEPT, otherwise INCONCLUSIVE). REASON: a model-chosen verdict can be steered by injected text and cannot be cross-checked. PROOF: `test_llm_cannot_choose_verdict_directly`, `test_malformed_llm_output_never_accepts`.

## D6 Who bears an INCONCLUSIVE outcome (confirmed by the user)
- DECISION: the agent: bond returned, no payment, budget back to the creator. REASON: the agent controls evidence quality; this also prevents the creator from locking funds. TRADEOFF: agents work for free on vague tasks. MITIGATION: criteria are visible before bidding. PROOF: `test_inconclusive_puts_risk_on_agent`.

## D7 Application appeal
- DECISION: one appeal per task, only by the party the verdict went against (either party on INCONCLUSIVE), fee equal to the bond, no new evidence in the MVP. Fee returns to the appellant if the verdict changed, otherwise goes to the counterparty. The re-evaluation is final. This is separate from GenLayer protocol appeals, which challenge a consensus round. PROOF: `test_appeal_rules`, `test_appeal_once_and_outcome_changes_fee_returned`, `test_failed_appeal_fee_goes_to_counterparty`.

## D8 Unreachable evidence reverts the submission
- QUESTION: what if a source is down at pin time? OPTIONS: (a) record and REJECT, (b) revert. DECISION: (b). REASON found in self-review: (a) charged an honest agent its bond for an outage it could have retried. PROOF: `test_unreachable_sources_revert_submission_and_agent_can_retry`.

## D9 No manifest hash, no reputation counters
- A hash adds nothing the contract verifies: the manifest fields are stored and no setter exists. Adding `hashlib` would add a library whose availability inside GenVM is unverified. Reputation counters were dropped with D2. PROOF: `test_criteria_are_immutable_no_setter_exists`.

## D10 Flat storage
- Nested `DynArray` inside a storage dataclass failed in Direct Mode on SDK v0.2.16, so bids and pins live in `TreeMap[str, ...]` keyed `"task_id:index"` with explicit counts. Bounded by MAX_BIDS=16 and MAX_URLS=3.

## D12 Payable methods never revert on invalid input
- Found in Studio: value attached to a reverted call stays on the contract. DECISION: validate in pure `_check_*` helpers, then refund the attached value into the sender's claimable (with a stored reason) instead of raising. TRADEOFF: invalid calls look like successful transactions (check the return value `-1` / `REFUNDED:`). PROOF: `test_failed_payable_calls_never_strand_value`; Studio re-check pending.

## D13 Adjudication timeout is a constructor argument
- QUESTION: how can a reviewer see `force_inconclusive` without waiting 7 days? DECISION: the timeout is fixed at deployment (60 s to 30 d). TRADEOFF: a short timeout lets anyone force INCONCLUSIVE sooner if nobody calls `adjudicate`; use long values for real deployments and 600 s only for the review build. PROOF: `test_short_timeout_build_reaches_force_inconclusive_in_minutes`, `test_constructor_rejects_out_of_range_timeout`.

## D14 Evidence pages must contain usable text
- Found by probing: pages whose text had no token of 3 ASCII characters (all Cyrillic pages, short JSON) made every validator reject the pin. DECISION: unicode-aware tokens; a reachable page with no usable text is pinned as `ok=false`; HTML entities are decoded. PROOF: `test_cyrillic_page_*`, `test_page_without_usable_text_*`, `test_html_entities_are_decoded`.

## D11 Pull payments, accounting first
- `withdraw` debits the balance, then emits the transfer. Real payout is not proven (KNOWN_LIMITATIONS L2).
