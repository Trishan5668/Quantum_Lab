"""Server-side Wolfram client boundary.

The integration is intentionally fail-closed: when credentials are absent
or Wolfram cannot be reached, callers receive an explicit unavailable
result instead of a locally fabricated "verified" answer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


class WolframUnavailableError(RuntimeError):
    """Raised when Wolfram cannot be used as the verification authority."""


@dataclass(frozen=True)
class WolframConfig:
    app_id: str | None
    api_key: str | None
    timeout_s: float = 12.0

    @classmethod
    def from_env(cls) -> "WolframConfig":
        timeout_raw = os.getenv("WOLFRAM_TIMEOUT_S", "12")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 12.0
        config = cls(
            app_id=os.getenv("WOLFRAM_APP_ID") or None,
            api_key=os.getenv("WOLFRAM_API_KEY") or None,
            timeout_s=timeout,
        )
        logger.info(
            "WolframConfig.from_env app_id=%s api_key=%s timeout_s=%s",
            _masked(config.app_id),
            _masked(config.api_key),
            config.timeout_s,
        )
        return config


_CACHE: dict[str, dict[str, Any]] = {}


class WolframClient:
    """Thin HTTP client for Wolfram evaluation.

    The default implementation records the exact Wolfram Language payload and
    uses WolframAlpha's JSON endpoint when an APP ID is configured. The parser
    normalizes Wolfram Alpha v2 pods into QuantumLab's verification schema;
    tests may replace this client with a deterministic fake that returns the
    same schema.
    """

    def __init__(self, config: WolframConfig | None = None) -> None:
        self.config = config or WolframConfig.from_env()

    async def evaluate_research(
        self,
        *,
        cache_key: str,
        wolfram_language: str,
    ) -> dict[str, Any]:
        if cache_key in _CACHE:
            logger.info("Wolfram research cache hit cache_key=%s", cache_key)
            return _CACHE[cache_key]
        if not self.config.app_id:
            logger.error("Wolfram research unavailable: WOLFRAM_APP_ID is not configured")
            raise WolframUnavailableError("WOLFRAM_APP_ID is not configured")

        params = {
            "appid": self.config.app_id,
            "input": wolfram_language,
            "output": "json",
            "format": "plaintext",
        }
        safe_params = {**params, "appid": _masked(self.config.app_id)}
        logger.info(
            "Wolfram request GET https://api.wolframalpha.com/v2/query params=%s",
            safe_params,
        )
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                resp = await client.get("https://api.wolframalpha.com/v2/query", params=params)
                logger.info(
                    "Wolfram response status=%s content_type=%s first_1000=%r",
                    resp.status_code,
                    resp.headers.get("content-type"),
                    resp.text[:1000],
                )
                resp.raise_for_status()
                logger.info("Parsing Wolfram response as JSON")
                payload = resp.json()
                print("WOLFRAM ACTUAL QUERY:", payload.get("queryresult", {}).get("inputstring"))
                print("WOLFRAM SUCCESS:", payload.get("queryresult", {}).get("success"))
                print("WOLFRAM ERROR:", payload.get("queryresult", {}).get("error"))
                print("WOLFRAM PODS:", payload.get("queryresult", {}).get("numpods"))
        except httpx.HTTPStatusError as exc:
            logger.exception(
                "Wolfram HTTP status error status=%s body_first_1000=%r",
                exc.response.status_code,
                exc.response.text[:1000],
            )
            if exc.response.status_code in {401, 403}:
                raise WolframUnavailableError("Wolfram authentication failed") from exc
            if exc.response.status_code == 429:
                raise WolframUnavailableError("Wolfram rate limit reached") from exc
            raise WolframUnavailableError(f"Wolfram HTTP error {exc.response.status_code}") from exc
        except json.JSONDecodeError as exc:
            logger.exception("Wolfram JSON parse failed")
            raise WolframUnavailableError("Wolfram response was not valid JSON") from exc
        except httpx.HTTPError as exc:
            logger.exception("Wolfram request failed before a valid JSON response was parsed")
            raise WolframUnavailableError("Wolfram request failed") from exc

        try:
            result = _extract_json_result(payload)
        except WolframUnavailableError:
            logger.exception("Wolfram response parser rejected the JSON payload")
            raise
        result["query_hash"] = cache_key
        _CACHE[cache_key] = result
        return result


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _extract_json_result(payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("queryresult") if isinstance(payload, dict) else None
    success_value = query.get("success") if isinstance(query, dict) else None
    error_value = query.get("error") if isinstance(query, dict) else None
    has_query = isinstance(query, dict)
    success_ok = _wolfram_bool(success_value) is True
    error_ok = _wolfram_bool(error_value) is False
    logger.info(
        "Wolfram JSON payload queryresult has_query=%s success=%r success_ok=%s error=%r error_ok=%s numpods=%s",
        has_query,
        success_value,
        success_ok,
        error_value,
        error_ok,
        query.get("numpods") if isinstance(query, dict) else None,
    )
    if not has_query or not success_ok or not error_ok:
        raise WolframUnavailableError("Wolfram did not return a successful computation")
    pods = query.get("pods") or []
    if not isinstance(pods, list) or not pods:
        raise WolframUnavailableError("Wolfram response did not include result pods")
    logger.info("Wolfram JSON payload pod_count=%s", len(pods) if isinstance(pods, list) else "not-list")
    normalized_pods: list[dict[str, Any]] = []
    for pod_index, pod in enumerate(pods):
        if not isinstance(pod, dict):
            continue
        subpods = pod.get("subpods") or []
        if not isinstance(subpods, list):
            subpods = []
        logger.info(
            "Inspecting Wolfram pod index=%s title=%r subpod_count=%s",
            pod_index,
            pod.get("title"),
            len(subpods),
        )
        normalized_subpods: list[dict[str, str]] = []
        for subpod_index, subpod in enumerate(subpods):
            if not isinstance(subpod, dict):
                continue
            text = subpod.get("plaintext")
            if not text:
                continue
            text = str(text)
            logger.info(
                "Inspecting Wolfram subpod index=%s plaintext_first_300=%r",
                subpod_index,
                text[:300],
            )
            normalized_subpods.append(
                {
                    "title": str(subpod.get("title") or ""),
                    "plaintext": text,
                }
            )
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                logger.info("Wolfram subpod plaintext is not JSON")
            else:
                if isinstance(parsed, dict):
                    logger.info("Wolfram subpod plaintext parsed as JSON object")
                    return parsed
        if normalized_subpods:
            normalized_pods.append(
                {
                    "title": str(pod.get("title") or ""),
                    "scanner": str(pod.get("scanner") or ""),
                    "subpods": normalized_subpods,
                }
            )
    if not normalized_pods:
        raise WolframUnavailableError("Wolfram response did not include usable plaintext result pods")
    return _normalized_verification_from_wolfram(query, normalized_pods)


def _normalized_verification_from_wolfram(
    query: dict[str, Any],
    pods: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "calculations": {
            "wolframAlpha": {
                "status": "VERIFIED",
                "input": str(query.get("inputstring") or ""),
                "pods": pods,
            },
            "gates": [],
            "embeddings": [],
            "stateEvolution": [],
            "circuitUnitary": {"status": "UNAVAILABLE"},
            "densityMatrix": {"status": "UNAVAILABLE"},
            "schmidt": {"status": "UNAVAILABLE"},
            "partialTrace": {"status": "UNAVAILABLE"},
            "entropy": {"status": "UNAVAILABLE"},
            "fidelity": {"status": "UNAVAILABLE"},
            "traceDistance": {"status": "UNAVAILABLE"},
            "purity": {"status": "UNAVAILABLE"},
            "correlations": {"status": "UNAVAILABLE"},
        },
        "wolframAlpha": {
            "success": True,
            "error": bool(query.get("error", False)),
            "numpods": query.get("numpods"),
            "inputstring": str(query.get("inputstring") or ""),
            "pods": pods,
        },
    }


def _masked(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 6:
        return "<set>"
    return f"<set:{value[:2]}...{value[-2:]} length={len(value)}>"


def _wolfram_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None
