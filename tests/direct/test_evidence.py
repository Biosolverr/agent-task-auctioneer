import pytest
from conftest import *

BAD_URLS = [
    "http://site1.org/a", "ftp://site1.org/a", "https://127.0.0.1/a", "https://10.0.0.5/a",
    "https://localhost/a", "https://intranet/a", "https://user:pw@site1.org/a",
    "https://site1.org:8080/a", "https://meta.internal/a", "javascript:alert(1)", "",
]


@pytest.mark.parametrize("url", BAD_URLS)
def test_disallowed_urls_rejected(env, url):
    tid = env.run_to_assigned()
    env.as_(env.a2)
    with env.vm.expect_revert("url not allowed"):
        env.c.submit_deliverable(tid, "x", [url])


def test_domain_allowlist_enforced(env):
    tid = env.new_task(domains="site1.org,site2.org")
    env.bid(tid, env.a1, 100 * 10**15)
    env.warp("2026-11-01T13:00:01+00:00")
    env.as_(env.rando)
    env.c.close_auction(tid)
    env.mock_pages()
    env.as_(env.a1)
    with env.vm.expect_revert("url not allowed"):
        env.c.submit_deliverable(tid, "x", ["https://site3.org/a"])
    with env.vm.expect_revert("url not allowed"):
        env.c.submit_deliverable(tid, "x", ["https://evil-site1.org/a"])
    env.c.submit_deliverable(tid, "x", ["https://www.site1.org/a", "https://site2.org/b"])


def test_duplicate_and_excess_urls_rejected(env):
    tid = env.run_to_assigned()
    env.mock_pages()
    env.as_(env.a2)
    with env.vm.expect_revert("distinct urls"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/a", "https://site1.org/a"])
    with env.vm.expect_revert("distinct urls"):
        env.c.submit_deliverable(tid, "x", [f"https://site{i}.org/a" for i in (1, 2, 3)] + ["https://site4.org/a"])
    with env.vm.expect_revert("distinct urls"):
        env.c.submit_deliverable(tid, "x", [])


def test_oversized_url_rejected(env):
    tid = env.run_to_assigned()
    env.as_(env.a2)
    with env.vm.expect_revert("url not allowed"):
        env.c.submit_deliverable(tid, "x", ["https://site1.org/" + "a" * 300])


def test_dead_url_is_pinned_as_unreachable(env):
    tid = env.run_to_assigned(min_sources=1)
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>alpha beta gamma delta alpha</p>"})
    env.vm.mock_web("site2.org", {"status": 404, "body": "gone"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a", "https://site2.org/a"])
    pins = env.c.get_task(tid)["pins"]
    assert pins[0]["ok"] is True and pins[1]["ok"] is False and pins[1]["excerpt"] == ""


def test_html_is_reduced_to_visible_text(env):
    tid = env.run_to_assigned(min_sources=1)
    env.vm.mock_web("site1.org", {"status": 200, "body":
        "<html><script>steal()</script><style>p{}</style><p>Visible content alpha beta</p></html>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    ex = env.c.get_task(tid)["pins"][0]["excerpt"]
    assert "Visible content" in ex and "steal" not in ex and "<" not in ex


def test_pinned_excerpt_is_size_bounded(env):
    tid = env.run_to_assigned(min_sources=1)
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>" + "word " * 5000 + "</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    assert len(env.c.get_task(tid)["pins"][0]["excerpt"]) <= 1200


def test_unstable_page_validator_disagrees(env):
    """Validator sees materially different content than the leader pinned -> no consensus."""
    tid = env.run_to_assigned(min_sources=1)
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>alpha beta gamma delta epsilon zeta</p>"})
    env.as_(env.a2)
    env.c.submit_deliverable(tid, "x", ["https://site1.org/a"])
    env.vm.clear_mocks()
    env.vm.mock_web("site1.org", {"status": 200, "body": "<p>completely different words appear here instead</p>"})
    assert env.vm.run_validator() is False


def test_stable_page_validator_agrees(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    assert env.vm.run_validator() is True


def test_validator_sees_dead_page_disagrees(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    env.vm.clear_mocks()
    env.mock_pages(ok=False)
    assert env.vm.run_validator() is False


def test_forged_leader_pin_rejected_by_validator(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    forged = [{"url": f"https://site{i}.org/a", "ok": True, "excerpt": "fabricated claims never on page zebra quantum"} for i in (1, 2, 3)]
    assert env.vm.run_validator(leader_result=forged) is False


def test_leader_error_during_pinning_rejected(env):
    tid = env.run_to_assigned()
    env.run_to_submitted(tid)
    from genlayer import gl
    assert env.vm.run_validator(leader_error=gl.vm.UserError("boom")) is False
