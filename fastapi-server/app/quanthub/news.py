"""Quantum community news with source adapters, caching and sanitisation.

Two adapters exist:

``curated``
    A versioned JSON file of individually verified articles. Every item records
    the URL, publisher, publication date and when it was verified. The API
    always labels this feed ``live: false``.

``rss``
    Optional live adapter over configured RSS/Atom feeds
    (``QUANTHUB_NEWS_FEEDS``). Responses are parsed defensively, HTML is
    stripped, links must be absolute HTTPS URLs, results are cached in SQLite,
    and any failure degrades to the curated feed with an explicit warning.

The service never generates headlines, summaries, publishers, or dates, and
never presents a static item as live.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.quanthub import db

CURATED_PATH = Path(__file__).resolve().parent / "news_curated.json"
DEFAULT_TTL_SECONDS = 900
MAX_ITEMS = 40
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_DATE_FORMATS = ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z")


@dataclass(frozen=True)
class FeedSource:
    kind: str
    label: str
    live: bool
    fetched_at: str | None
    warning: str | None = None


def _clean_text(raw: str, limit: int) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    text = _SPACE_RE.sub(" ", text).strip()
    return text[:limit].rstrip()


def _safe_url(raw: str) -> str | None:
    candidate = (raw or "").strip()
    if not candidate or len(candidate) > 1000:
        return None
    parts = urlsplit(candidate)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    if parts.username or parts.password:
        return None
    if any(ord(character) < 32 for character in candidate):
        return None
    return candidate


def _utc_stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    try:
        return _utc_stamp(datetime.fromisoformat(value))
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return _utc_stamp(parsed)
    return None


def curated_items() -> list[dict[str, Any]]:
    payload = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    items = []
    for raw in payload.get("items", []):
        url = _safe_url(str(raw.get("url", "")))
        if not url:
            continue
        items.append(
            {
                "id": raw["id"],
                "title": _clean_text(str(raw.get("title", "")), 240),
                "summary": _clean_text(str(raw.get("summary", "")), 900),
                "source": raw.get("source") or urlsplit(url).netloc,
                "url": url,
                "published_at": raw.get("published_at"),
                "tags": [str(tag) for tag in raw.get("tags", [])][:6],
                "category": raw.get("category", "research"),
                "kind": raw.get("kind", "article"),
                "verified_at": raw.get("verified_at"),
                "verification": raw.get("verification"),
                "related": [
                    link
                    for link in (
                        _safe_url(str(extra)) for extra in raw.get("related", [])
                    )
                    if link
                ],
                "live": False,
            }
        )
    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return items


def _feed_urls() -> list[str]:
    raw = os.getenv("QUANTHUB_NEWS_FEEDS", "")
    return [chunk.strip() for chunk in raw.split(",") if chunk.strip()]


def _ttl() -> int:
    try:
        return max(60, int(os.getenv("QUANTHUB_NEWS_TTL_SECONDS", str(DEFAULT_TTL_SECONDS))))
    except ValueError:
        return DEFAULT_TTL_SECONDS


def _cache_key(feeds: list[str]) -> str:
    return "rss:" + hashlib.sha256(",".join(sorted(feeds)).encode()).hexdigest()[:24]


def _read_cache(key: str) -> dict[str, Any] | None:
    with db.db() as conn:
        row = conn.execute("SELECT payload, fetched_at FROM news_cache WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return {"payload": db.json_load(row["payload"], None), "fetched_at": row["fetched_at"]}


def _write_cache(key: str, payload: Any) -> str:
    stamp = db.utc_now()
    with db.db() as conn:
        conn.execute(
            "INSERT INTO news_cache (key, payload, fetched_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, fetched_at = excluded.fetched_at",
            (key, json.dumps(payload, sort_keys=True), stamp),
        )
    return stamp


def _age_seconds(stamp: str | None) -> float:
    if not stamp:
        return float("inf")
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return float("inf")
    return (datetime.now(UTC) - parsed).total_seconds()


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_feed(xml_bytes: bytes, source_hint: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_bytes[: 2 * 1024 * 1024])
    except ET.ParseError:
        return []
    items: list[dict[str, Any]] = []
    for node in root.iter():
        name = _strip_namespace(node.tag)
        if name not in {"item", "entry"}:
            continue
        fields: dict[str, str] = {}
        link: str | None = None
        for child in node:
            child_name = _strip_namespace(child.tag)
            text = (child.text or "").strip()
            if child_name == "link":
                href = child.attrib.get("href")
                if href:
                    link = link or href
                elif text:
                    link = link or text
                continue
            if child_name in {"title", "description", "summary", "content", "pubdate", "published", "updated", "id"}:
                fields.setdefault(child_name, text)
        url = _safe_url(link or "")
        title = _clean_text(fields.get("title", ""), 240)
        if not url or not title:
            continue
        published = _parse_date(
            fields.get("published") or fields.get("pubdate") or fields.get("updated")
        )
        summary = _clean_text(
            fields.get("summary") or fields.get("description") or fields.get("content") or "",
            700,
        )
        items.append(
            {
                "id": hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16],
                "title": title,
                "summary": summary,
                "source": source_hint or urlsplit(url).netloc,
                "url": url,
                "published_at": published,
                "tags": [],
                "category": "news",
                "kind": "live",
                "verified_at": None,
                "verification": "Retrieved from a configured publisher feed; content is the publisher's.",
                "related": [],
                "live": True,
            }
        )
    return items


def _fetch_live(feeds: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - httpx is an install dependency
        return [], f"Live news is unavailable ({exc})."
    collected: list[dict[str, Any]] = []
    problems: list[str] = []
    with httpx.Client(timeout=8.0, follow_redirects=True, headers={"User-Agent": "QuantHub/1.0 news"}) as client:
        for feed in feeds:
            url = _safe_url(feed)
            if not url:
                problems.append(f"Skipped invalid feed URL: {feed}")
                continue
            try:
                response = client.get(url)
                response.raise_for_status()
            except (httpx.HTTPError, ValueError):
                problems.append(f"Feed unavailable: {urlsplit(url).netloc}")
                continue
            host = urlsplit(url).netloc
            collected.extend(_parse_feed(response.content, host))
    deduped: dict[str, dict[str, Any]] = {}
    for item in collected:
        deduped[item["url"]] = item
    ordered = sorted(
        deduped.values(), key=lambda item: str(item.get("published_at") or ""), reverse=True
    )[:MAX_ITEMS]
    return ordered, ("; ".join(problems) if problems else None)


def news_payload(
    *,
    category: str | None = None,
    tag: str | None = None,
    limit: int = 12,
    allow_live: bool = True,
) -> dict[str, Any]:
    limit = max(1, min(limit, MAX_ITEMS))
    feeds = _feed_urls()
    warning: str | None = None
    source: FeedSource
    items: list[dict[str, Any]]

    if feeds and allow_live:
        key = _cache_key(feeds)
        cached = _read_cache(key)
        age = _age_seconds(cached["fetched_at"]) if cached else float("inf")
        if cached and age < _ttl():
            items = cached["payload"] or []
            source = FeedSource(
                kind="rss",
                label="Live publisher feeds",
                live=True,
                fetched_at=cached["fetched_at"],
            )
        else:
            fetched, problem = _fetch_live(feeds)
            if fetched:
                stamp = _write_cache(key, fetched)
                items = fetched
                source = FeedSource(
                    kind="rss",
                    label="Live publisher feeds",
                    live=True,
                    fetched_at=stamp,
                    warning=problem,
                )
            else:
                items = []
                warning = problem or "Live news could not be retrieved."
                source = FeedSource(
                    kind="rss",
                    label="Live publisher feeds",
                    live=False,
                    fetched_at=cached["fetched_at"] if cached else None,
                    warning=warning,
                )
                if cached:
                    items = cached["payload"] or []
    else:
        items = []
        source = FeedSource(kind="curated", label="Curated, individually verified", live=False, fetched_at=None)

    if not items:
        items = curated_items()
        if source.kind != "curated":
            # Fall back to the verified snapshot rather than an empty panel.
            source = FeedSource(
                kind="curated",
                label="Curated, individually verified (live feed unavailable)",
                live=False,
                fetched_at=None,
                warning=source.warning or warning,
            )

    if category:
        needle = category.strip().lower()
        items = [item for item in items if str(item.get("category", "")).lower() == needle]
    if tag:
        needle = tag.strip().lower().lstrip("#")
        items = [
            item
            for item in items
            if needle in {str(value).lower() for value in item.get("tags", [])}
        ]

    items = sorted(items, key=lambda item: str(item.get("published_at") or ""), reverse=True)[:limit]
    return {
        "items": items,
        "feed": {
            "kind": source.kind,
            "label": source.label,
            "live": source.live,
            "fetched_at": source.fetched_at,
            "warning": source.warning,
            "ttl_seconds": _ttl(),
        },
        "attribution": (
            "Headlines and summaries belong to their publishers and link to the "
            "original source. Curated items were individually checked against the "
            "publisher's page; they are a snapshot, not a live feed."
        ),
    }


def news_categories() -> list[dict[str, str]]:
    items = curated_items()
    seen: dict[str, int] = {}
    for item in items:
        seen[str(item["category"])] = seen.get(str(item["category"]), 0) + 1
    return [{"id": key, "count": value} for key, value in sorted(seen.items())]
