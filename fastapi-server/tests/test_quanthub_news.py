"""Tests for the Quantum Community news panel and its source adapters."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from app.main import create_app
from app.quanthub import db as hub_db
from app.quanthub import news
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("QUANTHUB_ENV", "test")
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("QUANTHUB_NEWS_FEEDS", "")
    hub_db.reset_init_cache()
    with TestClient(create_app()) as test_client:
        yield test_client


def test_curated_feed_is_verified_and_not_labelled_live(client: TestClient) -> None:
    payload = client.get("/api/v1/community/news", params={"limit": 20}).json()["data"]
    assert payload["feed"]["kind"] == "curated"
    assert payload["feed"]["live"] is False
    assert len(payload["items"]) >= 6
    for item in payload["items"]:
        assert item["url"].startswith("https://")
        assert item["source"]
        assert item["published_at"]
        assert item["verified_at"]
        assert item["verification"]
        assert item["live"] is False
        assert item["summary"]
        assert len(item["title"]) <= 240


def test_curated_feed_includes_the_supplied_article(client: TestClient) -> None:
    items = client.get("/api/v1/community/news", params={"limit": 40}).json()["data"]["items"]
    article = next(
        item
        for item in items
        if item["url"].startswith("https://thequantuminsider.com/2026/10/17/")
    )
    assert "Claude" in article["title"]
    assert article["published_at"] == "2026-10-17"
    assert "Claude Mythos 5" in article["summary"]
    assert "eight" in article["summary"]
    assert "resource estimates" in article["summary"]
    assert any(link.startswith("https://arxiv.org/") for link in article["related"])


def test_news_category_and_tag_filters(client: TestClient) -> None:
    qec = client.get("/api/v1/community/news", params={"category": "qec", "limit": 40}).json()["data"]
    assert qec["items"]
    assert all(item["category"] == "qec" for item in qec["items"])

    tagged = client.get(
        "/api/v1/community/news", params={"tag": "reproducibility", "limit": 40}
    ).json()["data"]
    assert tagged["items"]
    assert all("reproducibility" in item["tags"] for item in tagged["items"])

    empty = client.get(
        "/api/v1/community/news", params={"tag": "not-a-real-topic", "limit": 40}
    ).json()["data"]
    assert empty["items"] == []


def test_live_feed_failure_degrades_to_curated(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "newsdata"))
    monkeypatch.setenv("QUANTHUB_NEWS_FEEDS", "https://127.0.0.1:9/unreachable.xml")
    hub_db.reset_init_cache()
    with TestClient(create_app()) as client:
        payload = client.get("/api/v1/community/news", params={"limit": 6}).json()["data"]
    assert payload["items"]
    assert payload["feed"]["live"] is False
    assert payload["feed"]["kind"] == "curated"
    assert payload["feed"]["warning"]
    assert "unavailable" in payload["feed"]["warning"].lower()


def test_feed_parsing_strips_markup_and_rejects_unsafe_links() -> None:
    rss = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Feed</title>
      <item>
        <title>Real headline</title>
        <link>https://example.org/article</link>
        <description>&lt;p&gt;Summary with &lt;b&gt;markup&lt;/b&gt;.&lt;/p&gt;</description>
        <pubDate>Tue, 14 Jul 2026 10:00:00 +0000</pubDate>
      </item>
      <item>
        <title>Unsafe</title>
        <link>javascript:alert(1)</link>
        <description>bad</description>
      </item>
    </channel></rss>"""
    items = news._parse_feed(rss, "example.org")
    assert len(items) == 1
    item = items[0]
    assert item["url"] == "https://example.org/article"
    assert item["title"] == "Real headline"
    assert "<p>" not in item["summary"]
    assert item["published_at"].startswith("2026-07-14")
    assert item["live"] is True


def test_url_sanitiser_rejects_unsafe_schemes() -> None:
    assert news._safe_url("javascript:alert(1)") is None
    assert news._safe_url("data:text/html,<script>") is None
    assert news._safe_url("https://user:pass@example.org/x") is None
    assert news._safe_url("https://example.org/article") == "https://example.org/article"


def test_categories_endpoint_is_derived_from_verified_items() -> None:
    categories = {entry["id"] for entry in news.news_categories()}
    assert {"qec", "hardware", "software", "algorithms", "benchmarks"} <= categories
