# ECONOMIC_MODEL

Units: integer wei. `bond = floor(budget * 1000 / 10000)`. `price` = winning bid <= budget.

| Outcome | Agent claimable | Creator claimable |
|---|---|---|
| ACCEPT | price + bond | budget - price |
| REJECT | 0 (bond forfeited) | budget + bond |
| INCONCLUSIVE | bond | budget |
| ABANDONED | 0 | budget + bond |
| NO_BIDS / CANCELLED | n/a | budget |
| Appeal fee (== bond) | to appellant if the verdict changed, else to the counterparty | |
| Losing bidders | bond | |

Real-balance check: `solvency()` returns balance, liabilities and `solvent`; it must read `solvent: true` after every step in Studio (not provable in Direct Mode, L12).

Accounted pools: held in tasks (budget, bonds, appeal fee), `claimable_total`, `total_out`. Identity checked by `accounting()` after every step of every fuzz walk: `total_in - total_out == held_in_tasks + claimable_total`.

Incentives. Bidding below cost costs the 10% bond if the agent abandons or fails. A creator gains nothing from bidding on its own task through another wallet (it pays itself). A creator can profit from unsatisfiable criteria only by taking bonds (THREAT F6), which is why criteria are public before bidding and one appeal exists. `MIN_BUDGET` = 0.001 GEN exists because two consensus rounds cost more than trivial tasks are worth. The real protocol fee per round was NOT measured, so the minimum is a placeholder (KNOWN_LIMITATIONS L5).
