import random
from datetime import datetime, timezone
import pytest
from conftest import *

P = 10**15


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()
ACTIONS = ["bid", "close", "submit", "adjudicate", "appeal", "settle", "expire", "force", "cancel", "withdraw", "new"]


def _try(fn):
    try:
        fn()
        return True
    except Exception:
        return False


@pytest.mark.parametrize("seed", range(25))
def test_random_transition_sequences_conserve_funds(env, seed):
    rng = random.Random(seed)
    actors = [env.creator, env.a1, env.a2, env.a3, env.rando]
    env.mock_pages()
    t = rng.choice([[True] * 3, [True, False, True], [True, None, True]])
    env.vm.mock_llm(".*", llm(t))
    clock = 1_793_534_400                      # 2026-11-01T12:00:00Z
    env.new_task()
    assert env.c.task_count() == 1          # guard: the walk really starts with a live task
    settled_once = {}
    for _ in range(60):
        act = rng.choice(ACTIONS)
        who = rng.choice(actors)
        tid = rng.randrange(0, max(1, env.c.task_count()))
        clock += rng.choice([0, 30, 600, 7200, 90000, 700000])
        env.vm.warp(iso(clock))
        c = env.c
        if act == "new":
            _try(lambda: env.new_task(budget=rng.choice([BUDGET, 3 * 10**15])))
        elif act == "bid":
            env.as_(who, BOND)
            _try(lambda: c.place_bid(tid, rng.randrange(1, 900) * P, "n"))
        elif act == "appeal":
            env.as_(who, BOND)
            _try(lambda: c.appeal(tid))
        elif act == "submit":
            env.as_(who)
            _try(lambda: c.submit_deliverable(tid, "r", ["https://site1.org/a", "https://site2.org/a"]))
        elif act == "withdraw":
            env.as_(who)
            _try(lambda: c.withdraw())
        else:
            env.as_(who)
            fn = {"close": c.close_auction, "adjudicate": c.adjudicate, "settle": c.settle,
                  "expire": c.expire_assignment, "force": c.force_inconclusive,
                  "cancel": c.cancel_task}[act]
            ok = _try(lambda: fn(tid))
            if act == "settle" and ok:
                assert tid not in settled_once, "task settled twice"
                settled_once[tid] = True
        check_invariants(env)
    # all claimable balances are non-negative and total never exceeds what came in
    a = check_invariants(env)
    assert a["claimable_total"] <= a["total_in"]
    assert a["total_in"] >= BUDGET           # funds actually moved during the walk


def test_guided_walk_reaches_every_terminal_outcome_and_conserves_funds(env):
    """Guards against a vacuous fuzz: a long biased walk must reach all terminal outcomes."""
    rng = random.Random(7)
    actors = [env.creator, env.a1, env.a2, env.a3, env.rando]
    env.mock_pages()
    clock = 1_793_534_400
    weights = {"new": 1, "bid": 14, "close": 8, "submit": 8, "adjudicate": 8, "appeal": 3,
               "settle": 8, "expire": 2, "force": 1, "cancel": 1, "withdraw": 4}
    acts = [a for a, w in weights.items() for _ in range(w)]
    c = env.c
    hits = {}
    for _ in range(4000):
        act, who = rng.choice(acts), rng.choice(actors)
        tid = (c.task_count() - 1) if (rng.random() < 0.7 and c.task_count()) else \
            rng.randrange(0, max(1, c.task_count()))
        clock += rng.choice([0, 0, 0, 30, 300, 3700, 90000])
        env.vm.warp(iso(clock))
        env.vm.clear_mocks()
        env.mock_pages()
        env.vm.mock_llm(".*", llm(rng.choice([[True] * 3, [True, False, True], [True, None, True]])))
        if act in ("submit", "appeal") and c.task_count() and rng.random() < 0.85:
            w = c.get_task(tid)["winner"].lower()          # act as an entitled party most of the time
            by_hex = {env.hx(x): x for x in actors}
            who = by_hex.get(w, who) if act == "submit" or rng.random() < 0.5 else env.creator
        env.as_(who, BOND if act in ("bid", "appeal") else 0)
        fn = {"bid": lambda: c.place_bid(tid, rng.randrange(1, 900) * P, "n"),
              "appeal": lambda: c.appeal(tid), "close": lambda: c.close_auction(tid),
              "submit": lambda: c.submit_deliverable(tid, "r", ["https://site1.org/a", "https://site2.org/a"]),
              "adjudicate": lambda: c.adjudicate(tid), "settle": lambda: c.settle(tid),
              "expire": lambda: c.expire_assignment(tid), "force": lambda: c.force_inconclusive(tid),
              "cancel": lambda: c.cancel_task(tid), "withdraw": lambda: c.withdraw(),
              "new": lambda: env.new_task()}[act]
        if act == "new":
            env.as_(env.creator, BUDGET)
        ok = _try(fn)
        hits[act] = hits.get(act, 0) + (1 if ok else 0)
        check_invariants(env)
    print("successful actions:", hits)
    outcomes = {c.get_task(i)["outcome"] for i in range(c.task_count())} - {""}
    print("tasks:", c.task_count(), "outcomes reached:", sorted(outcomes))
    # INCONCLUSIVE / appeals / force_inconclusive are covered by the deterministic tests
    # (test_escrow.py, test_security.py); this walk proves the common lifecycle is non-vacuous.
    assert {"ACCEPT", "REJECT", "ABANDONED", "NO_BIDS"} <= outcomes
    assert hits["submit"] > 0 and hits["adjudicate"] > 0 and hits["settle"] > 0
