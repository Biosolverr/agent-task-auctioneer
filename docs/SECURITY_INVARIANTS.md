# SECURITY_INVARIANTS

| # | Invariant | Enforced by | Checked by |
|---|---|---|---|
| I1 | `total_in - total_out == held_in_tasks + claimable_total` always (counter identity) | every credit/debit path | `check_invariants` after every step of 26 walks |
| I1b | the contract's real balance covers `held_in_tasks + claimable_total` | `solvency()` view | view logic in Direct Mode (`test_solvency_view_...`); in hosted Studio `solvent` was true and `surplus` 0 after every runbook block (simulated balances, L12) |
| I2 | A task budget is accounted exactly once and the budget plus the winning bond is paid out exactly once | single `settle` per task, status check | `test_task_never_pays_both_parties_the_budget` |
| I3 | A SETTLED or CANCELLED task never changes | status guards on every write call | `test_terminal_task_cannot_reopen`, `test_refund_after_release_impossible` |
| I4 | One winner per task | `close_auction` only from OPEN | `test_one_task_has_one_winner` |
| I5 | Criteria cannot change after creation | no setter exists | `test_criteria_are_immutable_no_setter_exists` |
| I6 | Only the assigned agent submits; only a party the verdict went against appeals | caller checks | `test_agent_cannot_submit_for_another_agent`, `test_appeal_rules` |
| I7 | A malformed or injected model output never yields ACCEPT | verdict derived by code from per-criterion flags | `test_malformed_llm_output_never_accepts`, `test_llm_cannot_choose_verdict_directly`, `test_unknown_values_become_null_not_true` |
| I8 | Every non-terminal state has a permissionless exit | `close_auction`, `expire_assignment`, `force_inconclusive`, `settle` | `test_no_task_stays_locked_without_participant_action` |
| I9 | Withdrawal debits before it transfers and cannot repeat | `withdraw` ordering | `test_withdraw_debits_before_transfer_and_cannot_repeat` |
| I10 | Claimable balances never exceed funds received | I1 | `test_guided_walk_reaches_every_terminal_outcome_and_conserves_funds` |
| I11 | All money is integer wei; no floats | code review (the only float is the 0.6 token-overlap ratio, never used for money) | review |

Not covered: I1b on a real network and I9 against a failing real transfer (L2, L12).
