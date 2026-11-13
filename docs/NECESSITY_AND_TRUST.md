# NECESSITY_AND_TRUST

## GenLayer Necessity Test
Remove GenLayer and rebuild conventionally. What is lost:

| Component | Without GenLayer | Level |
|---|---|---|
| Fetching and pinning evidence (consensus round 1) | a backend fetches pages; the buyer must trust that backend, nobody can re-check | 3 mechanism-critical |
| Per-criterion evaluation re-run by validators (round 2) | a backend calls an LLM; a single trusted judge | 3 mechanism-critical |
| Fixed-evidence appeals | reproducible only if the backend stored the pages and is honest | 2 materially useful |
| Reverse auction, bond, escrow, pull payout | an ordinary EVM contract does this | 0-1 replaceable |

Conclusion: GenLayer is structurally necessary for the judgment, not for the market around it. A reviewer may say the auction is decoration; the answer is that it exists to give the judgment something to settle (see Scope cut).

## Trust Map
| Boundary | Classification | Rule |
|---|---|---|
| User -> contract call | untrusted | all inputs bounded; caller checked per function |
| Creator criteria | untrusted but immutable | public before bidding; cannot be edited |
| Agent deliverable text | untrusted data | stored cleaned; shown to the model only inside `<untrusted>` |
| Web pages | untrusted evidence | become state only after validators agree on reachability and content overlap; stored as bounded text |
| Leader output | untrusted | every validator recomputes or re-fetches |
| Model output | untrusted | reduced to per-criterion true/false/null; verdict derived by code |
| Consensus result | trusted for agreement only | not a claim of truth |
| Validator web layer (DNS, redirects, private networks) | partially trusted | outside contract control (L3) |
| Native value / balances | trusted platform | actual transfer path unproven (L2) |

## Scope cut ("if removed, does the core break?")
- Pinning, per-criterion evaluation, deterministic verdict, settlement: core, kept.
- Auction + bond: the judgment needs a counterparty and a price; kept, but removable without breaking the core mechanism (a creator could appoint an agent).
- Appeal: not core; kept because a single consensus verdict on a vague criterion is the weakest point. Could be cut to simplify.
- `force_inconclusive`, `expire_assignment`: liveness; required by the "no stuck funds" rule.
- Reputation, manifest hash: cut.
