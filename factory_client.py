"""Factory Analytics API client with parallel fetches and error handling."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

BASE_URL = "https://api.factory.ai/api/v1/analytics"


def _get_headers() -> dict:
    key = os.getenv("FACTORY_API_KEY") or st.session_state.get("factory_api_key", "")
    return {"Authorization": f"Bearer {key}", "Accept": "application/json"}


def _yesterday_utc() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def _default_start(end: str) -> str:
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=14)
    return start_dt.strftime("%Y-%m-%d")


def _fetch(endpoint: str, params: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=_get_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_analytics(start_date: str | None = None, end_date: str | None = None) -> dict:
    """Fetch all four productivity endpoints in parallel.

    Returns a dict with keys: tokens, tools, activity, productivity.
    Each value is the parsed JSON or a dict with {'_error': str}.
    """
    end = end_date or _yesterday_utc()
    start = start_date or _default_start(end)

    endpoints = {
        "tokens": "tokens",
        "tools": "tools",
        "activity": "activity",
        "productivity": "productivity",
    }

    results: dict = {}
    errors: dict = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch, ep, {"startDate": start, "endDate": end}): name
            for name, ep in endpoints.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response else 0
                detail = ""
                try:
                    detail = exc.response.json().get("detail", "")
                except Exception:
                    detail = exc.response.text[:200] if exc.response else ""
                errors[name] = {"status": status, "detail": detail}
                results[name] = {"_error": f"{status}: {detail}"}
            except Exception as exc:
                errors[name] = {"status": 0, "detail": str(exc)}
                results[name] = {"_error": str(exc)}

    results["_errors"] = errors
    results["_meta"] = {"start_date": start, "end_date": end}
    return results


def fetch_users(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    max_pages: int = 5,
) -> dict:
    """Fetch per-user metrics from the /users endpoint.

    Walks cursor-based pagination up to `max_pages` to gather enough
    rows for a leaderboard. Returns {'data': [...], 'meta': {...},
    '_error': str | None}.
    """
    end = end_date or _yesterday_utc()
    start = start_date or _default_start(end)

    aggregated: list[dict] = []
    cursor: str | None = None
    last_meta: dict = {}
    error: str | None = None

    for _ in range(max_pages):
        params: dict = {"startDate": start, "endDate": end, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        try:
            page = _fetch("users", params)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else 0
            detail = ""
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200] if exc.response else ""
            error = f"{status}: {detail}"
            break
        except Exception as exc:
            error = str(exc)
            break

        aggregated.extend(page.get("data", []))
        last_meta = page.get("meta", {}) or {}
        if not last_meta.get("has_more"):
            break
        cursor = last_meta.get("next_cursor")
        if not cursor:
            break

    return {"data": aggregated, "meta": last_meta, "_error": error}
