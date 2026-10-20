"""Shared test bootstrap.

Two guarantees for the whole suite:

1. **Tests never touch a real deployment.**  The environment is pinned at
   import time (before any test module imports ``app.main`` and therefore
   before the module-level application is built) to the ``test`` environment
   with unverified identity headers explicitly enabled, an isolated data
   directory, and no Firebase project configured.  Without this, importing
   ``app.main`` would create a runtime database next to the source tree.
2. **No accidental network identity.**  Firebase variables are cleared so a
   developer shell containing production credentials cannot be used by tests.

Individual tests may still override these values with ``monkeypatch``.
"""

from __future__ import annotations

import os
import tempfile

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="quanthub-tests-")

os.environ["QUANTHUB_ENV"] = "test"
os.environ["QUANTHUB_TRUST_CLIENT_IDENTITY"] = "1"
os.environ["QUANTHUB_DATA_DIR"] = _TEST_DATA_DIR
os.environ["QUANTHUB_NEWS_FEEDS"] = ""
for _name in ("FIREBASE_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "QUANTHUB_FIREBASE_PROJECT"):
    os.environ.pop(_name, None)

TEST_DATA_DIR = _TEST_DATA_DIR
