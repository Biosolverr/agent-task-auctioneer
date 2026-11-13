# CONSENSUS_MODEL

What consensus gives: validators agree, under the contract's own equivalence rule, on (1) what each submitted URL returned and (2) which verdict the criteria imply for that evidence. It does not establish that the sources are true or that the verdict is objectively correct.

Rules used (current GenLayer docs): custom leader/validator functions via `gl.vm.run_nondet_unsafe`; the validator must re-run the work instead of only checking the output format; exact HTML equality is never required.

Round 1, pinning. Compared: URL list, per-URL reachability, containment of the leader excerpt in the validator's own fetch (>= 60% of tokens). Not compared: byte equality, headers, ordering of page text beyond containment.
Round 2, evaluation. Compared: the derived verdict. Not compared: the free-text reason. The leader's `passes` list must have the right length. An invalid leader result, a leader error or a verdict mismatch makes the validator return False.

Failure handling: malformed model output -> INCONCLUSIVE (never ACCEPT); model or web failure inside the block -> transaction fails, state unchanged; repeated non-agreement -> 7-day `force_inconclusive` fallback, so funds cannot stay locked.

Protocol finality: an accepted transaction can still be recomputed by a protocol appeal until finalization. Internal credits are recomputed with it. The actual outbound transfer (`withdraw`) is emitted from a state-changing call and relies on finalization semantics that were NOT exercised here (L2).

Direct Mode honesty: `run_validator` in the tests simulates one validator with mocked inputs. It checks the validator logic, not real multi-validator agreement.
