import pytest
from conftest import *


def test_winner_submits_and_evidence_is_pinned(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    t = env.c.get_task(tid)
    assert t["status"] == 2 and len(t["pins"]) == 3 and all(p["ok"] for p in t["pins"])
    assert "Report number 1" in t["pins"][0]["excerpt"]
    check_invariants(env)


def test_unauthorized_submission_rejected(env):
    tid = env.run_to_assigned()          # winner is a2
    env.mock_pages()
    for who in (env.a1, env.creator, env.rando):
        env.as_(who)
        with env.vm.expect_revert("not the assigned agent"):
            env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])


def test_submit_before_assignment_rejected(env):
    tid = env.new_task()
    env.as_(env.a1)
    with env.vm.expect_revert("not the assigned agent"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])


def test_submit_after_deadline_rejected(env):
    tid = env.run_to_assigned()
    env.warp("2026-11-03T00:00:00+00:00")
    env.mock_pages()
    env.as_(env.a2)
    with env.vm.expect_revert("deadline passed"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])


def test_second_submission_rejected(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    env.as_(env.a2)
    with env.vm.expect_revert("not the assigned agent"):
        env.c.submit_deliverable(tid, "again", ["https://site1.org/a"])


def test_oversized_result_rejected(env):
    tid = env.run_to_assigned()
    env.mock_pages()
    env.as_(env.a2)
    with env.vm.expect_revert("bad result length"):
        env.c.submit_deliverable(tid, "x" * 4001, ["https://site1.org/a"])
    with env.vm.expect_revert("bad result length"):
        env.c.submit_deliverable(tid, "", ["https://site1.org/a"])


def test_abandonment_forfeits_bond_and_refunds_budget(env):
    tid = env.run_to_assigned()
    env.warp("2026-11-03T00:00:00+00:00")
    env.as_(env.rando)
    env.c.expire_assignment(tid)
    t = env.c.get_task(tid)
    assert t["status"] == 5 and t["outcome"] == "ABANDONED"
    assert env.claim(env.creator) == BUDGET + BOND and env.claim(env.a2) == 0
    with env.vm.expect_revert("not expirable"):
        env.c.expire_assignment(tid)
    check_invariants(env)


def test_expire_before_deadline_rejected(env):
    tid = env.run_to_assigned()
    env.as_(env.rando)
    with env.vm.expect_revert("not expirable"):
        env.c.expire_assignment(tid)
