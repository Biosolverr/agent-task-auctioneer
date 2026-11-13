import pytest
from conftest import *

P = 10**15


def test_criteria_are_immutable_no_setter_exists(env):
    tid = env.new_task()
    before = env.c.get_task(tid)
    for name in ("update_task", "set_criteria", "edit_task", "update_criteria"):
        assert not hasattr(env.c, name)
    assert env.c.get_task(tid) == before


def test_agent_cannot_submit_for_another_agent(env):
    tid = env.run_to_assigned()
    env.mock_pages()
    env.as_(env.a1)
    with env.vm.expect_revert("not the assigned agent"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])


def test_nobody_but_parties_can_redirect_funds(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.as_(env.rando)
    expect_refund(env, env.rando, 0, lambda: env.c.appeal(tid), "not entitled")
    env.settle_after_window(tid)
    assert env.claim(env.rando) == 0
    env.as_(env.rando)
    with env.vm.expect_revert("nothing to withdraw"):
        env.c.withdraw()


def test_terminal_task_cannot_reopen(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.settle_after_window(tid)
    env.as_(env.a1, BOND)
    expect_refund(env, env.a1, BOND, lambda: env.c.place_bid(tid, 100 * P, "late"), "bidding closed")
    env.as_(env.rando)
    for fn in (env.c.close_auction, env.c.adjudicate, env.c.settle, env.c.expire_assignment):
        with env.vm.expect_revert():
            fn(tid)
    env.as_(env.creator)
    with env.vm.expect_revert():
        env.c.cancel_task(tid)


def test_one_task_has_one_winner(env):
    tid = env.run_to_assigned()
    w = env.c.get_task(tid)["winner"]
    env.as_(env.rando)
    with env.vm.expect_revert("not open"):
        env.c.close_auction(tid)
    assert env.c.get_task(tid)["winner"] == w


def test_cancel_after_assignment_rejected(env):
    tid = env.run_to_assigned()
    env.as_(env.creator)
    with env.vm.expect_revert("cannot cancel"):
        env.c.cancel_task(tid)


def test_refund_after_release_impossible(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.settle_after_window(tid)
    env.as_(env.creator)
    for fn in (env.c.cancel_task, env.c.expire_assignment):
        with env.vm.expect_revert():
            fn(tid)
    assert env.claim(env.creator) == BUDGET - 400 * P


def test_max_values_and_oversized_note_are_bounded(env):
    tid = env.new_task(budget=10**30)
    env.as_(env.a1, 10**30 // 10)
    env.c.place_bid(tid, 10**30, "n" * 5000)
    check_invariants(env)


def test_appeal_rules(env):
    tid = env.run_to_adjudicated([True] * 3)               # ACCEPT: only creator may appeal
    env.as_(env.a2, BOND)
    expect_refund(env, env.a2, BOND, lambda: env.c.appeal(tid), "not entitled")
    env.as_(env.creator, BOND - 1)
    expect_refund(env, env.creator, BOND - 1, lambda: env.c.appeal(tid), "appeal fee")
    env.warp("2026-11-03T00:00:00+00:00")
    env.as_(env.creator, BOND)
    expect_refund(env, env.creator, BOND, lambda: env.c.appeal(tid), "window closed")


def test_appeal_once_and_outcome_changes_fee_returned(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.as_(env.creator, BOND)
    env.c.appeal(tid)
    env.as_(env.creator, BOND)
    expect_refund(env, env.creator, BOND, lambda: env.c.appeal(tid), "not appealable")
    env.vm.clear_mocks()
    env.vm.mock_llm(".*", llm([True, False, True]))
    env.as_(env.rando)
    assert env.c.adjudicate(tid) == "REJECT"                 # final, window closed
    assert env.c.get_task(tid)["appeal_deadline"] == 0
    env.as_(env.rando)
    env.c.settle(tid)
    # refund + forfeited bond + appeal fee back + the rejected second appeal's value refunded
    assert env.claim(env.creator) == BUDGET + BOND + BOND + BOND
    check_invariants(env)


def test_failed_appeal_fee_goes_to_counterparty(env):
    tid = env.run_to_adjudicated([True] * 3)
    env.as_(env.creator, BOND)
    env.c.appeal(tid)
    env.as_(env.rando)
    assert env.c.adjudicate(tid) == "ACCEPT"                 # same mock -> unchanged
    env.c.settle(tid)
    assert env.claim(env.a2) == 400 * P + BOND + BOND        # price + bond + creator's lost fee
    check_invariants(env)


def test_stuck_adjudication_falls_back_to_inconclusive(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    env.as_(env.rando)
    with env.vm.expect_revert("not stuck"):
        env.c.force_inconclusive(tid)
    env.warp("2026-11-12T00:00:00+00:00")
    env.c.force_inconclusive(tid)
    env.c.settle(tid)
    assert env.claim(env.creator) == BUDGET and env.claim(env.a2) == BOND
    check_invariants(env)


def test_stuck_reevaluation_keeps_original_verdict(env):
    tid = env.run_to_adjudicated([True, False, True])        # REJECT
    env.as_(env.a2, BOND)
    env.c.appeal(tid)
    env.warp("2026-11-12T00:00:00+00:00")
    env.as_(env.rando)
    env.c.force_inconclusive(tid)
    env.c.settle(tid)
    assert env.c.get_task(tid)["verdict"] == "REJECT"
    # re-evaluation never finished: the original verdict stands and the appeal fee is returned
    assert env.claim(env.creator) == BUDGET + BOND
    assert env.claim(env.a2) == BOND
    check_invariants(env)


def test_no_task_stays_locked_without_participant_action(env):
    """Every non-terminal state has a permissionless exit."""
    t_open = env.new_task()
    t_assigned = env.run_to_assigned(close_at="2026-11-01T14:00:02+00:00")
    t_sub = env.run_to_assigned(close_at="2026-11-01T15:00:03+00:00")
    env.run_to_submitted(t_sub)
    env.warp("2026-12-30T00:00:00+00:00")
    env.as_(env.rando)
    env.c.close_auction(t_open)
    env.c.expire_assignment(t_assigned)
    env.c.force_inconclusive(t_sub)
    env.c.settle(t_sub)
    assert [env.c.get_task(i)["status"] for i in (t_open, t_assigned, t_sub)] == [6, 5, 5]
    assert check_invariants(env)["held_in_tasks"] == 0


def test_failed_payable_calls_never_strand_value(env):
    """Studio keeps value sent with a reverted call; payable methods must therefore refund via claimable."""
    tid = env.new_task()
    sent = 0
    for who, value, call in [
        (env.a1, 7, lambda: env.c.place_bid(tid, 100 * P, "n")),              # wrong bond
        (env.creator, BOND, lambda: env.c.place_bid(tid, 100 * P, "n")),      # creator bidding
        (env.a2, 5 * P, lambda: env.c.appeal(tid)),                           # not appealable
        (env.a3, 3, lambda: env.c.place_bid(99, 100 * P, "n")),               # no such task
        (env.rando, 11, lambda: env.c.create_task("", CRITERIA, "", 2, 3600, 86400, 86400)),
    ]:
        env.as_(who, value)
        before = env.claim(who)
        call()
        assert env.claim(who) == before + value
        sent += value
    a = check_invariants(env)
    assert a["claimable_total"] == sent                 # every refunded wei is withdrawable, none stranded
    env.as_(env.a1)
    assert env.c.withdraw() == 7
