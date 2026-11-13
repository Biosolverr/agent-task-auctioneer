import pytest
from conftest import *


def test_create_task_ok(env):
    tid = env.new_task()
    t = env.c.get_task(tid)
    assert tid == 0 and t["status"] == 0 and t["budget"] == BUDGET and t["bond"] == BOND
    check_invariants(env)


def test_task_ids_are_sequential(env):
    assert env.new_task() == 0 and env.new_task() == 1 and env.c.task_count() == 2


@pytest.mark.parametrize("kw,msg", [
    (dict(budget=10**15 - 1), "budget below minimum"),
    (dict(budget=0), "budget below minimum"),
    (dict(criteria=[]), "criteria required"),
    (dict(criteria=["c"] * 9), "criteria required"),
    (dict(criteria=["x" * 301]), "bad criterion"),
    (dict(criteria=["line1\nline2"]), "bad criterion"),
    (dict(min_sources=0), "min_sources"),
    (dict(min_sources=4), "min_sources"),
    (dict(bid_secs=59), "window"),
    (dict(delivery_secs=90 * 86400 + 1), "window"),
    (dict(domains="Bad_Domain!"), "bad domains"),
])
def test_invalid_creation_is_refunded_not_reverted(env, kw, msg):
    expect_refund(env, env.creator, kw.get("budget", BUDGET), lambda: env.new_task(**kw), msg)
    assert env.c.task_count() == 0


def test_oversized_description_rejected(env):
    env.as_(env.creator, BUDGET)
    expect_refund(env, env.creator, BUDGET,
                  lambda: env.c.create_task("x" * 1501, CRITERIA, "", 2, 3600, 86400, 86400), "description")


def test_nonexistent_task_id(env):
    env.as_(env.rando)
    with env.vm.expect_revert("no such task"):
        env.c.close_auction(99)
    with env.vm.expect_revert("no such task"):
        env.c.get_task(0)
