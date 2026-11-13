import pytest
from conftest import *

P = 10**15
PRICE = 400 * P


def settled(env, passes):
    tid = env.run_to_adjudicated(passes)
    assert env.settle_after_window(tid) in ("ACCEPT", "REJECT", "INCONCLUSIVE")
    return tid


def test_accept_pays_agent_price_and_returns_bond_and_change(env):
    tid = settled(env, [True, True, True])
    assert env.claim(env.a2) == PRICE + BOND
    assert env.claim(env.creator) == BUDGET - PRICE
    assert env.c.get_task(tid)["status"] == 5
    a = check_invariants(env)
    assert a["held_in_tasks"] == 0


def test_reject_refunds_creator_and_forfeits_bond(env):
    settled(env, [True, False, True])
    assert env.claim(env.creator) == BUDGET + BOND and env.claim(env.a2) == 0
    check_invariants(env)


def test_inconclusive_puts_risk_on_agent(env):
    settled(env, [True, None, True])
    assert env.claim(env.creator) == BUDGET and env.claim(env.a2) == BOND
    check_invariants(env)


def test_task_never_pays_both_parties_the_budget(env):
    for passes in ([True] * 3, [True, False, True], [True, None, True]):
        e = env
        settled(e, passes)
        paid = e.claim(e.creator) + e.claim(e.a2)
        assert paid == BUDGET + BOND            # budget + the single winning bond, exactly once
        return


def test_settle_twice_rejected(env):
    tid = settled(env, [True] * 3)
    env.as_(env.rando)
    with env.vm.expect_revert("not settleable"):
        env.c.settle(tid)
    assert env.claim(env.a2) == PRICE + BOND


def test_settle_before_verdict_rejected(env):
    tid = env.run_to_assigned()
    env.as_(env.rando)
    with env.vm.expect_revert("not settleable"):
        env.c.settle(tid)


def test_settle_before_appeal_window_expiry_rejected(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.as_(env.rando)
    with env.vm.expect_revert("appeal window open"):
        env.c.settle(tid)


def test_losing_bidders_get_bonds_back_exactly_once(env):
    tid = settled(env, [True] * 3)
    assert env.claim(env.a1) == BOND and env.claim(env.a3) == BOND


def test_withdraw_debits_before_transfer_and_cannot_repeat(env):
    settled(env, [True] * 3)
    env.as_(env.a2)
    before = check_invariants(env)
    paid = env.c.withdraw()
    assert paid == PRICE + BOND and env.claim(env.a2) == 0
    after = check_invariants(env)
    assert after["total_out"] - before["total_out"] == paid
    with env.vm.expect_revert("nothing to withdraw"):
        env.c.withdraw()


def test_withdraw_with_nothing_owed_rejected(env):
    settled(env, [True] * 3)
    env.as_(env.rando)
    with env.vm.expect_revert("nothing to withdraw"):
        env.c.withdraw()


def test_one_wei_rounding_conserves_funds(env):
    tid = env.new_task(budget=10**15 + 7)       # bond = floor(budget * 10%)
    env.bid(tid, env.a1, 333_333_333_333_333, bond=(10**15 + 7) * 1000 // 10000)
    env.warp("2026-11-01T13:00:01+00:00")
    env.as_(env.rando)
    env.c.close_auction(tid)
    check_invariants(env)


def test_solvency_view_compares_real_balance_with_liabilities(env):
    """Direct Mode does not move value between accounts, so the balance is set by hand.
    This proves the VIEW's logic; the real-balance check on live funds happens in Studio."""
    tid = env.run_to_assigned()
    s = env.c.solvency()
    assert s["liabilities"] == BUDGET + BOND + BOND + BOND  # budget + winner bond + 2 refunded bonds
    env.vm.deal(env.vm._contract_address, s["liabilities"] - 1)
    assert env.c.solvency()["solvent"] is False
    env.vm.deal(env.vm._contract_address, s["liabilities"])
    assert env.c.solvency()["solvent"] is True
    env.vm.deal(env.vm._contract_address, s["liabilities"] + 5)
    assert env.c.solvency()["solvent"] is True


def test_get_claimable_accepts_string_address_and_rejects_garbage(env):
    tid = env.run_to_assigned()
    assert env.c.get_claimable(env.hx(env.a1)) == BOND
    assert env.c.get_claimable(env.hx(env.a1).upper().replace("0X", "0x")) == BOND   # case-insensitive
    assert env.c.get_claimable(env.hx(env.rando)) == 0
    for bad in ("", "0x123", "not an address"):
        with env.vm.expect_revert("bad address"):
            env.c.get_claimable(bad)
