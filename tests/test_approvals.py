"""Approval queue tests."""

from brain.approvals import queue as approval_queue


def test_enqueue_approve_deny(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "")

    aid = approval_queue.enqueue("draft", "Hello team", {"message": "test"})
    assert aid
    pending = approval_queue.pending()
    assert any(p["id"] == aid for p in pending)

    out = approval_queue.approve(aid, "Hello team — edited")
    assert out["status"] == "ok"
    assert out["kind"] == "draft"

    aid2 = approval_queue.enqueue("draft", "Second")
    denied = approval_queue.deny(aid2)
    assert denied["status"] == "ok"
    assert approval_queue.get(aid2)["status"] == "denied"


def test_meta_weather_connect_source(monkeypatch):
    from brain.cockpit.read import CockpitRead

    for key in (
        "META_ACCESS_TOKEN",
        "META_AD_ACCOUNT_ID",
        "WEATHER_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    c = CockpitRead()
    m = c.meta_ads()
    assert m["status"] == "connect_source"
    assert m["sources"] == ["meta"]
    w = c.weather()
    assert w["status"] == "connect_source"
    assert w["sources"] == ["weather"]
