import pytest
from conftest import *

P = 10**15


def test_valid_bid_and_bond_accounting(env):
    tid = env.new_task()
    env.bid(tid, env.a1, 500 * P)
    assert env.c.get_task(tid)["bids"] == 1
    a = check_invariants(env)
    assert a["held_in_tasks"] == BUDGET + BOND


@pytest.mark.parametrize("price,bond,msg", [
    (0, BOND, "price must be"), (BUDGET + 1, BOND, "price must be"),
    (500 * P, BOND - 1, "exact bond"), (500 * P, BOND + 1, "exact bond"), (500 * P, 0, "exact bond"),
])
def test_invalid_bids(env, price, bond, msg):
    tid = env.new_task()
    env.as_(env.a1, bond)
    expect_refund(env, env.a1, bond, lambda: env.c.place_bid(tid, price, "n"), msg)


def test_duplicate_bid_rejected(env):
    tid = env.new_task()
    env.bid(tid, env.a1, 500 * P)
    expect_refund(env, env.a1, BOND, lambda: env.bid(tid, env.a1, 100 * P), "one bid per address")


def test_creator_cannot_bid(env):
    tid = env.new_task()
    expect_refund(env, env.creator, BOND, lambda: env.bid(tid, env.creator, 100 * P), "creator cannot bid")


def test_bid_after_deadline_rejected(env):
    tid = env.new_task()
    env.warp("2026-11-01T13:00:01+00:00")
    expect_refund(env, env.a1, BOND, lambda: env.bid(tid, env.a1, 100 * P), "bidding closed")


def test_close_before_deadline_rejected(env):
    tid = env.new_task()
    env.bid(tid, env.a1, 100 * P)
    env.as_(env.rando)
    with env.vm.expect_revert("still running"):
        env.c.close_auction(tid)


def test_lowest_price_wins_and_losers_refunded(env):
    tid = env.run_to_assigned(prices=(500, 400, 700))
    t = env.c.get_task(tid)
    assert t["status"] == 1 and t["winner"].lower() == env.hx(env.a2) and t["price"] == 400 * P
    assert env.claim(env.a1) == BOND and env.claim(env.a3) == BOND
    assert env.claim(env.a2) == 0
    check_invariants(env)


def test_tie_broken_by_earliest_bid(env):
    tid = env.run_to_assigned(prices=(400, 400, 400))
    assert env.c.get_task(tid)["winner"].lower() == env.hx(env.a1)


def test_close_twice_rejected(env):
    tid = env.run_to_assigned()
    with env.vm.expect_revert("not open"):
        env.c.close_auction(tid)


def test_no_bids_refunds_creator(env):
    tid = env.new_task()
    env.warp("2026-11-01T13:00:01+00:00")
    env.as_(env.rando)
    env.c.close_auction(tid)
    t = env.c.get_task(tid)
    assert t["status"] == 6 and t["outcome"] == "NO_BIDS"
    assert env.claim(env.creator) == BUDGET
    check_invariants(env)


def test_bid_cap(env):
    from gltest.direct import create_test_addresses
    tid = env.new_task()
    for w in create_test_addresses(40)[10:26]:
        env.bid(tid, w, 100 * P)
    expect_refund(env, env.a1, BOND, lambda: env.bid(tid, env.a1, 100 * P), "bid cap")


def test_cancel_only_by_creator_and_only_without_bids(env):
    tid = env.new_task()
    env.as_(env.rando)
    with env.vm.expect_revert("creator only"):
        env.c.cancel_task(tid)
    env.bid(tid, env.a1, 100 * P)
    env.as_(env.creator)
    with env.vm.expect_revert("cannot cancel"):
        env.c.cancel_task(tid)
    tid2 = env.new_task()
    env.as_(env.creator)
    env.c.cancel_task(tid2)
    assert env.claim(env.creator) == BUDGET
    with env.vm.expect_revert("cannot cancel"):
        env.c.cancel_task(tid2)
    check_invariants(env)
