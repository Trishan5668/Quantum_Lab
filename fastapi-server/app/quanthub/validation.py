"""Validation helpers for project metadata, paths and user-supplied strings."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit

from app.quanthub.errors import bad_request

# Slugs that would collide with application routes or reserved system names.
RESERVED_SLUGS = {
    "about",
    "admin",
    "api",
    "app",
    "assets",
    "blog",
    "community",
    "docs",
    "explore",
    "favicon.ico",
    "feed",
    "history",
    "learn",
    "login",
    "logout",
    "new",
    "notifications",
    "profile",
    "projects",
    "qec",
    "register",
    "research",
    "robots.txt",
    "settings",
    "simulator",
    "static",
    "support",
    "trending",
    "users",
}

_NAME_RE = re.compile(r"^[\w .\-]+$", re.UNICODE)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def clean_name(raw: str) -> str:
    name = (raw or "").strip()
    name = re.sub(r"\s+", " ", name)
    if not name:
        raise bad_request("InvalidName", "A project name is required.")
    if len(name) > 100:
        raise bad_request("InvalidName", "Project names must be 100 characters or fewer.")
    if name in {".", ".."}:
        raise bad_request("InvalidName", "That name is not allowed.")
    if not _NAME_RE.match(name):
        raise bad_request(
            "InvalidName",
            "Project names may only contain letters, numbers, spaces, '.', '-', and '_'.",
        )
    if not any(character.isalnum() for character in name):
        raise bad_request("InvalidName", "Project names must contain a letter or number.")
    return name


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = normalized.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-._")
    slug = slug[:100].strip("-._")
    return slug or "project"


def clean_slug(raw: str) -> str:
    slug = (raw or "").strip().lower()
    if not slug:
        raise bad_request("InvalidSlug", "A project slug is required.")
    if len(slug) > 100:
        raise bad_request("InvalidSlug", "The slug must be 100 characters or fewer.")
    if not _SLUG_RE.match(slug):
        raise bad_request(
            "InvalidSlug",
            "Slugs must start with a letter or number and may contain lowercase "
            "letters, numbers, '.', '-', and '_'.",
        )
    if ".." in slug or slug.endswith((".", "-", "_")):
        raise bad_request("InvalidSlug", "That slug is not allowed.")
    if slug in RESERVED_SLUGS:
        raise bad_request("ReservedSlug", f"'{slug}' is reserved by the platform.", slug=slug)
    return slug


def clean_description(raw: str | None) -> str:
    description = (raw or "").strip()
    if len(description) > 350:
        raise bad_request(
            "InvalidDescription", "Descriptions must be 350 characters or fewer."
        )
    if _CONTROL_RE.search(description):
        raise bad_request("InvalidDescription", "Descriptions may not contain control characters.")
    return description


def clean_topics(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    topics: list[str] = []
    for item in raw:
        topic = (item or "").strip().lower().lstrip("#")
        if not topic:
            continue
        if len(topic) > 35:
            raise bad_request("InvalidTopic", f"Topic '{topic}' is longer than 35 characters.")
        if not _TOPIC_RE.match(topic):
            raise bad_request(
                "InvalidTopic",
                f"Topic '{topic}' must contain only lowercase letters, numbers, '.', '-', and '_'.",
            )
        if topic not in topics:
            topics.append(topic)
    if len(topics) > 20:
        raise bad_request("InvalidTopic", "A project may have at most 20 topics.")
    return topics


def clean_visibility(raw: str | None) -> str:
    visibility = (raw or "public").strip().lower()
    if visibility not in {"public", "private"}:
        raise bad_request("InvalidVisibility", "Visibility must be 'public' or 'private'.")
    return visibility


def clean_website(raw: str | None) -> str | None:
    if raw is None:
        return None
    website = raw.strip()
    if not website:
        return None
    if len(website) > 500:
        raise bad_request("InvalidWebsite", "Website URLs must be 500 characters or fewer.")
    parts = urlsplit(website)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise bad_request("InvalidWebsite", "Enter a full URL starting with http:// or https://.")
    if _CONTROL_RE.search(website):
        raise bad_request("InvalidWebsite", "That URL contains invalid characters.")
    return website


def clean_commit_message(raw: str | None, *, default: str, max_length: int = 500) -> str:
    message = (raw or "").strip() or default
    message = _CONTROL_RE.sub("", message)
    if len(message) > max_length:
        message = message[: max_length - 1].rstrip() + "…"
    return message


def clean_experiment_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise bad_request("InvalidExperimentName", "An experiment name is required.")
    if len(name) > 120:
        raise bad_request(
            "InvalidExperimentName", "Experiment names must be 120 characters or fewer."
        )
    return name
