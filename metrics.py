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


def hands_off_share(tools_df: pd.DataFrame) -> float:
    if tools_df.empty or "tool_autonomy_level_ratio" not in tools_df.columns:
        return 0.0
    total = 0.0
    count = 0
    for row in tools_df["tool_autonomy_level_ratio"]:
        if isinstance(row, dict):
            auto = row.get("auto_high", 0) + row.get("auto_medium", 0)
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
                totals[k] += row.get(k, 0)
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


def build_users_df(raw: dict) -> pd.DataFrame:
    return _safe_df(raw.get("data", []))


def _mode_or_first(series: pd.Series) -> Any:
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    mode = cleaned.mode()
    return mode.iloc[0] if not mode.empty else cleaned.iloc[0]


def _flatten_languages(values: pd.Series) -> str:
    seen: dict[str, int] = {}
    for entry in values.dropna():
        if isinstance(entry, list):
            for item in entry:
                if isinstance(item, dict):
                    name = item.get("language") or item.get("name")
                    count = item.get("count", 1)
                elif isinstance(item, str):
                    name = item
                    count = 1
                else:
                    continue
                if not name:
                    continue
                seen[name] = seen.get(name, 0) + int(count or 0)
    if not seen:
        return ""
    ordered = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
    return ", ".join(name for name, _ in ordered[:3])


def power_user_leaderboard(users_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Aggregate per-user-per-day rows into a leaderboard sorted by tool_calls.

    Per-user PR counts are not exposed by the Analytics API, so we rank by
    tool_calls (the closest per-user output proxy) and surface autonomy and
    delegation alongside it.
    """
    if users_df.empty or "user_id" not in users_df.columns:
        return pd.DataFrame()

    df = users_df.copy()
    numeric_cols = [
        "tool_calls",
        "billable_tokens",
        "sessions",
        "messages",
        "user_messages",
        "assistant_messages",
        "autonomy_ratio",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    label_col = "user_email" if "user_email" in df.columns else "user_id"
    df[label_col] = df[label_col].fillna(df["user_id"])

    sum_cols = [
        c
        for c in [
            "tool_calls",
            "billable_tokens",
            "sessions",
            "messages",
            "user_messages",
            "assistant_messages",
        ]
        if c in df.columns
    ]

    agg_map: dict[str, Any] = {c: "sum" for c in sum_cols}
    if "autonomy_ratio" in df.columns:
        agg_map["autonomy_ratio"] = "mean"
    if "delegation_level" in df.columns:
        agg_map["delegation_level"] = _mode_or_first
    if "primary_model" in df.columns:
        agg_map["primary_model"] = _mode_or_first
    if "languages" in df.columns:
        agg_map["languages"] = _flatten_languages

    grouped = (
        df.groupby(["user_id", label_col], dropna=False)
        .agg(agg_map)
        .reset_index()
    )

    if "tool_calls" in grouped.columns:
        grouped = grouped.sort_values("tool_calls", ascending=False)

    grouped = grouped.head(n).reset_index(drop=True)
    grouped.insert(0, "rank", range(1, len(grouped) + 1))

    if "autonomy_ratio" in grouped.columns:
        grouped["autonomy_ratio"] = grouped["autonomy_ratio"].round(2)
    int_cols = [
        "billable_tokens",
        "tool_calls",
        "sessions",
        "messages",
        "user_messages",
        "assistant_messages",
    ]
    for col in int_cols:
        if col in grouped.columns:
            grouped[col] = grouped[col].astype("Int64")

    return grouped
