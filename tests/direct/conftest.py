from pathlib import Path
import json
import pytest
from gltest.direct import VMContext, deploy_contract, create_test_addresses

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "agent_task_auctioneer.py"
ADJ_TIMEOUT = 7 * 86400          # constructor argument used by the default fixture
SDK_VERSION = "v0.2.16"   # pinned: "latest" (v0.3.0-rc7) ships no universal tarball
GEN = 10**18
BUDGET = GEN
BOND = BUDGET * 1000 // 10000
CRITERIA = ["Cites three distinct sources", "Each source published in 2026", "Summary under 200 words"]
T0 = "2026-11-01T12:00:00+00:00"


class Env:
    def __init__(self):
        (self.creator, self.a1, self.a2, self.a3, self.rando) = create_test_addresses(5)
        self.vm = VMContext()
        self.vm.warp(T0)
        self.vm.check_pickling = True
        self.vm.sender = self.creator
        self.c = None

    def hx(self, who):
        return "0x" + bytes(who).hex()

    def claim(self, who):
        return self.c.get_claimable(self.hx(who))

    def as_(self, who, value=0):
        self.vm.sender = who
        self.vm.value = value

    def new_task(self, budget=BUDGET, criteria=None, domains="", min_sources=2,
                 bid_secs=3600, delivery_secs=86400, appeal_secs=86400):
        self.as_(self.creator, budget)
        return self.c.create_task("Find sources on topic X", CRITERIA if criteria is None else criteria, domains,
                                  min_sources, bid_secs, delivery_secs, appeal_secs)

    def bid(self, tid, who, price, bond=BOND):
        self.as_(who, bond)
        return self.c.place_bid(tid, price, "claims: web research")

    def warp(self, ts):
        self.vm.warp(ts)

    def mock_pages(self, ok=True):
        for i in (1, 2, 3):
            if ok:
                self.vm.mock_web(f"site{i}.org", {"status": 200, "body": f"<html><p>Report number {i} published 2026 about topic X with findings alpha beta gamma delta epsilon</p></html>"})
            else:
                self.vm.mock_web(f"site{i}.org", {"status": 404, "body": "gone"})

    def run_to_assigned(self, prices=(500, 400, 700), close_at="2026-11-01T13:00:01+00:00", min_sources=2):
        tid = self.new_task(min_sources=min_sources)
        for who, p in zip((self.a1, self.a2, self.a3), prices):
            self.bid(tid, who, p * 10**15)
        self.warp(close_at)
        self.as_(self.rando)
        self.c.close_auction(tid)
        return tid

    def run_to_adjudicated(self, passes, tid=None):
        tid = self.run_to_assigned() if tid is None else tid
        self.run_to_submitted(tid)
        self.vm.mock_llm(".*", llm(passes))
        self.as_(self.rando)
        self.c.adjudicate(tid)
        return tid

    def settle_after_window(self, tid):
        self.warp("2026-11-03T00:00:00+00:00")
        self.as_(self.rando)
        return self.c.settle(tid)

    def run_to_submitted(self, tid, winner=None):
        self.mock_pages()
        self.as_(winner or self.a2)
        self.c.submit_deliverable(tid, "Summary: three sources found.", [f"https://site{i}.org/a" for i in (1, 2, 3)])


def llm(passes, reason="ok", **extra):
    d = {"passes": passes, "reason": reason}
    d.update(extra)
    return json.dumps(d)


def check_invariants(e):
    a = e.c.accounting()
    assert a["total_in"] - a["total_out"] == a["held_in_tasks"] + a["claimable_total"], a
    return a


def expect_refund(e, who, value, call, msg):
    """A rejected payable call must not revert: it refunds `value` to the sender's claimable."""
    before = e.claim(who)
    out = call()
    assert out == -1 or str(out).startswith("REFUNDED"), out
    assert e.claim(who) == before + value
    assert msg in e.c.get_last_rejection(e.hx(who)), e.c.get_last_rejection(e.hx(who))
    check_invariants(e)


@pytest.fixture
def env():
    e = Env()
    with e.vm.activate():
        e.c = deploy_contract(CONTRACT, e.vm, ADJ_TIMEOUT, sdk_version=SDK_VERSION)
        yield e


@pytest.fixture
def env_short():
    """Same contract deployed with a 600 s adjudication timeout (the Studio review build)."""
    e = Env()
    with e.vm.activate():
        e.c = deploy_contract(CONTRACT, e.vm, 600, sdk_version=SDK_VERSION)
        yield e
