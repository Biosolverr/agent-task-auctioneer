"""Defects found after the first Studio runs, plus transparency views."""
import pytest
from conftest import *

P = 10**15


def single_source_task(env):
    return env.run_to_assigned(min_sources=1)


def test_get_task_exposes_the_immutable_manifest(env):
    tid = env.new_task(domains="site1.org", min_sources=1)
    t = env.c.get_task(tid)
    assert t["criteria"] == CRITERIA and t["description"] == "Find sources on topic X"
    assert t["domains"] == "site1.org" and t["min_sources"] == 1
    assert t["delivery_secs"] == 86400 and t["appeal_secs"] == 86400


def test_get_task_exposes_submission_and_appeal_fields(env):
    tid = env.run_to_adjudicated([True, False, True])
    env.as_(env.a2, BOND)
    env.c.appeal(tid)
    t = env.c.get_task(tid)
    assert t["result"].startswith("Summary") and t["submitted_at"] > 0
    assert t["appellant"].lower() == env.hx(env.a2) and t["appeal_fee"] == BOND
    assert t["status"] == 4


def test_get_bid_lists_every_bid(env):
    tid = env.run_to_assigned(prices=(500, 400, 700))
    bids = [env.c.get_bid(tid, i) for i in range(3)]
    assert [b["price"] for b in bids] == [500 * P, 400 * P, 700 * P]
    assert bids[1]["bidder"].lower() == env.hx(env.a2) and "web research" in bids[0]["note"]
    with env.vm.expect_revert("no such bid"):
        env.c.get_bid(tid, 3)


def test_contract_info(env):
    i = env.c.contract_info()
    assert i["version"] == "ata-2" and i["adjudication_timeout_secs"] == ADJ_TIMEOUT
    assert i["bond_bps"] == 1000 and i["max_bids"] == 16


@pytest.mark.parametrize("bad", [0, 59, 30 * 86400 + 1])
def test_constructor_rejects_out_of_range_timeout(bad):
    e = Env()
    with e.vm.activate():
        with pytest.raises(Exception):
            deploy_contract(CONTRACT, e.vm, bad, sdk_version=SDK_VERSION)


def test_short_timeout_build_reaches_force_inconclusive_in_minutes(env_short):
    env = env_short
    assert env.c.contract_info()["adjudication_timeout_secs"] == 600
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    env.warp("2026-11-01T13:09:00+00:00")             # < 600 s after submission
    env.as_(env.rando)
    with env.vm.expect_revert("not stuck"):
        env.c.force_inconclusive(tid)
    env.warp("2026-11-01T13:15:00+00:00")             # > 600 s
    env.c.force_inconclusive(tid)
    assert env.c.get_task(tid)["verdict"] == "INCONCLUSIVE"
    env.c.settle(tid)
    assert env.claim(env.creator) == BUDGET and env.claim(env.a2) == BOND
    check_invariants(env)


def test_cyrillic_page_can_be_pinned_and_validators_agree(env):
    tid = single_source_task(env)
    env.vm.mock_web("site1.org", {"status": 200, "body":
        "<p>Привет мир, это страница про блокчейн и смарт контракты на русском языке</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    pin = env.c.get_task(tid)["pins"][0]
    assert pin["ok"] is True and "блокчейн" in pin["excerpt"]
    assert env.vm.run_validator() is True


def test_cyrillic_page_changed_content_still_disagrees(env):
    tid = single_source_task(env)
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>Привет мир это страница про блокчейн</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    env.vm.clear_mocks()
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>Совсем другой текст про погоду и кошек</p>"})
    assert env.vm.run_validator() is False


@pytest.mark.parametrize("body", ['{"a": 1}', "", "<html><script>x()</script></html>", "<p>--- ... !!!</p>"])
def test_page_without_usable_text_is_unreachable_not_a_consensus_failure(env, body):
    tid = single_source_task(env)
    env.vm.mock_web("site1.org", {"status": 200, "body": body})
    env.as_(env.a2)
    with env.vm.expect_revert("insufficient reachable evidence"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    assert env.vm.run_validator() is True            # leader and validator agree: ok=false
    assert env.c.get_task(tid)["status"] == 1


def test_html_entities_are_decoded(env):
    tid = single_source_task(env)
    env.vm.mock_web("site1.org", {"status": 200, "body":
        "<p>Domain&nbsp;Names &amp; Registry &#169; &#x41; &unknown; text</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    ex = env.c.get_task(tid)["pins"][0]["excerpt"]
    assert "&nbsp;" not in ex and "Domain Names & Registry" in ex and "©" in ex and "A" in ex
    assert "&unknown;" not in ex


def test_invalid_numeric_entity_is_dropped_safely(env):
    tid = single_source_task(env)
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>alpha &#xD800; &#99999999; beta gamma</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    assert env.c.get_task(tid)["pins"][0]["excerpt"] == "alpha beta gamma"


def test_appeal_reevaluation_timeout_returns_the_fee(env):
    tid = env.run_to_adjudicated([True, False, True])
    env.as_(env.a2, BOND)
    env.c.appeal(tid)
    env.warp("2026-11-12T00:00:00+00:00")
    env.as_(env.rando)
    env.c.force_inconclusive(tid)
    env.c.settle(tid)
    assert env.claim(env.a2) == BOND                  # fee back, not forfeited
    check_invariants(env)
