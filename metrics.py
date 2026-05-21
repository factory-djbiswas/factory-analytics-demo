"""Derived metric calculations from raw Factory Analytics data."""

from typing import Any

import pandas as pd


def _safe_df(data: list[dict]) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def _pct_change(series: pd.Series) -> float | None:
    if series.empty or series.iloc[0] == 0:
        return None
    return round(((series.iloc[-1] - series.iloc[0]) / series.iloc[0]) * 100, 1)


def build_activity_df(raw: dict) -> pd.DataFrame:
    return _safe_df(raw.get("data", []))


def build_tools_df(raw: dict) -> pd.DataFrame:
    return _safe_df(raw.get("data", []))


def build_productivity_df(raw: dict) -> pd.DataFrame:
    return _safe_df(raw.get("data", []))


def build_tokens_df(raw: dict) -> pd.DataFrame:
    return _safe_df(raw.get("data", []))


def total_prs(productivity_df: pd.DataFrame) -> int:
    if productivity_df.empty or "git_prs_created" not in productivity_df.columns:
        return 0
    return int(productivity_df["git_prs_created"].sum())


def total_commits(productivity_df: pd.DataFrame) -> int:
    if productivity_df.empty or "git_commits" not in productivity_df.columns:
        return 0
    return int(productivity_df["git_commits"].sum())


def avg_autonomy_ratio(tools_df: pd.DataFrame) -> float:
    if tools_df.empty or "autonomy_ratio_avg" not in tools_df.columns:
        return 0.0
    return round(tools_df["autonomy_ratio_avg"].mean(), 2)


def peak_dau(activity_df: pd.DataFrame) -> int:
    if activity_df.empty or "daily_active_users" not in activity_df.columns:
        return 0
    return int(activity_df["daily_active_users"].max())


def autonomy_trend_pct(tools_df: pd.DataFrame) -> float | None:
    if tools_df.empty or "autonomy_ratio_avg" not in tools_df.columns:
        return None
    return _pct_change(tools_df["autonomy_ratio_avg"])


def pr_velocity_change(productivity_df: pd.DataFrame) -> float | None:
    if productivity_df.empty or "git_prs_created" not in productivity_df.columns:
        return None
    prs = productivity_df["git_prs_created"]
    if len(prs) < 6:
        return _pct_change(prs)
    first_avg = prs.iloc[:3].mean()
    last_avg = prs.iloc[-3:].mean()
    if first_avg == 0:
        return None
    return round(((last_avg - first_avg) / first_avg) * 100, 1)


def files_per_dau(activity_df: pd.DataFrame, productivity_df: pd.DataFrame) -> pd.DataFrame:
    if activity_df.empty or productivity_df.empty:
        return pd.DataFrame()
    a = activity_df[["date", "daily_active_users"]].copy()
    p = productivity_df[["date", "files_edited"]].copy()
    merged = a.merge(p, on="date", how="inner")
    merged["files_per_dau"] = merged["files_edited"] / merged["daily_active_users"].replace(0, pd.NA)
    return merged


def _num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def hands_off_share(tools_df: pd.DataFrame) -> float:
    if tools_df.empty or "tool_autonomy_level_ratio" not in tools_df.columns:
        return 0.0
    total = 0.0
    count = 0
    for row in tools_df["tool_autonomy_level_ratio"]:
        if isinstance(row, dict):
            auto = _num(row.get("auto_high")) + _num(row.get("auto_medium"))
            total += auto
            count += 1
    if count == 0:
        return 0.0
    return round(total / count * 100, 1)


def delegation_distribution(tools_df: pd.DataFrame) -> dict[str, float]:
    if tools_df.empty or "tool_autonomy_level_ratio" not in tools_df.columns:
        return {}
    keys = ["auto_high", "auto_medium", "auto_low", "spec", "manual"]
    totals = {k: 0.0 for k in keys}
    count = 0
    for row in tools_df["tool_autonomy_level_ratio"]:
        if isinstance(row, dict):
            for k in keys:
                totals[k] += _num(row.get(k))
            count += 1
    if count == 0:
        return {}
    return {k: round(v / count * 100, 1) for k, v in totals.items()}


def top_languages(productivity_df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    if productivity_df.empty or "by_language" not in productivity_df.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for day in productivity_df["by_language"]:
        if isinstance(day, list):
            for item in day:
                if isinstance(item, dict):
                    rows.append(item)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "language" not in df.columns or "count" not in df.columns:
        return pd.DataFrame()
    return df.groupby("language")["count"].sum().sort_values(ascending=False).head(n).reset_index()


def client_dau_breakdown(activity_df: pd.DataFrame) -> pd.DataFrame:
    if activity_df.empty or "daily_active_users_by_client" not in activity_df.columns:
        return pd.DataFrame()
    records = []
    for _, row in activity_df.iterrows():
        clients = row.get("daily_active_users_by_client", {})
        if isinstance(clients, dict):
            for client, count in clients.items():
                records.append({"date": row["date"], "client": client, "dau": count})
    return pd.DataFrame(records)
