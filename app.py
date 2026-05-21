"""Streamlit entry point for Factory Analytics Productivity Demo."""

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from charts import (
    adoption_area_chart,
    autonomy_chart,
    delegation_donut,
    kpi_tile,
    killer_chart,
    output_amplification_chart,
    top_languages_chart,
)
from factory_client import fetch_analytics, fetch_users
from metrics import (
    avg_autonomy_ratio,
    autonomy_trend_pct,
    build_activity_df,
    build_productivity_df,
    build_tools_df,
    build_tokens_df,
    build_users_df,
    client_dau_breakdown,
    delegation_distribution,
    files_per_dau,
    hands_off_share,
    peak_dau,
    power_user_leaderboard,
    pr_velocity_change,
    top_languages,
    total_commits,
    total_prs,
)

load_dotenv()

st.set_page_config(
    page_title="Factory Analytics — Productivity Demo",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar: Auth & Date Range ───────────────────────────────────────────────
with st.sidebar:
    st.title("🏭 Factory Analytics")
    st.caption("Productivity Metrics Dashboard")

    api_key = os.getenv("FACTORY_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "Factory API Key",
            type="password",
            placeholder="fk-...",
            help="Get yours at app.factory.ai/settings/api-keys",
        )
        if api_key:
            os.environ["FACTORY_API_KEY"] = api_key
            st.session_state["factory_api_key"] = api_key
    else:
        st.success("API key loaded from environment")

    st.divider()

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    default_end = yesterday.date()
    default_start = (yesterday - timedelta(days=14)).date()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=default_start)
    with col2:
        end_date = st.date_input("End Date", value=default_end)

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    if end_date >= datetime.now(timezone.utc).date():
        st.warning("Analytics has a 24-hour lag. Adjusting to yesterday.")
        end_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    st.divider()
    st.caption("v1.0  •  Built with Streamlit")

# ── Fetch Data ───────────────────────────────────────────────────────────────
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

if not api_key:
    st.warning("Enter your Factory API key in the sidebar to continue.")
    st.stop()

with st.spinner("Fetching analytics from Factory API..."):
    results = fetch_analytics(start_date=start_str, end_date=end_str)

errors = results.get("_errors", {})
if errors:
    for name, err in errors.items():
        if err["status"] == 401:
            st.error("Invalid API key (401). Check your key in the sidebar.")
            st.stop()
        elif err["status"] == 403:
            st.error("Insufficient permissions (403). Manager or Owner role required.")
            st.stop()
        elif err["status"] == 400 and "today" in err.get("detail", "").lower():
            st.warning(f"Adjusted date for {name}: cannot query today's date.")
        else:
            st.error(f"Error fetching {name}: {err['detail']}")

# Build DataFrames
activity_df = build_activity_df(results.get("activity", {}))
tools_df = build_tools_df(results.get("tools", {}))
prod_df = build_productivity_df(results.get("productivity", {}))
tokens_df = build_tokens_df(results.get("tokens", {}))

if activity_df.empty and tools_df.empty and prod_df.empty:
    st.info("No data returned for this date range. Try a wider window.")
    st.stop()

# ── KPI Row ──────────────────────────────────────────────────────────────────
st.header("Productivity at a Glance")

kpi_cols = st.columns(4)
with kpi_cols[0]:
    prs = total_prs(prod_df)
    pr_delta = pr_velocity_change(prod_df)
    delta_str = f"{pr_delta:+.1f}% velocity" if pr_delta is not None else ""
    st.markdown(kpi_tile("Total PRs Created", f"{prs:,}", delta=delta_str), unsafe_allow_html=True)

with kpi_cols[1]:
    commits = total_commits(prod_df)
    st.markdown(kpi_tile("Total Commits", f"{commits:,}"), unsafe_allow_html=True)

with kpi_cols[2]:
    auto = avg_autonomy_ratio(tools_df)
    auto_delta = autonomy_trend_pct(tools_df)
    delta_str = f"{auto_delta:+.1f}% trend" if auto_delta is not None else ""
    st.markdown(kpi_tile("Avg Autonomy Ratio", f"{auto:.1f}", delta=delta_str), unsafe_allow_html=True)

with kpi_cols[3]:
    dau = peak_dau(activity_df)
    st.markdown(kpi_tile("Peak DAU", f"{dau:,}"), unsafe_allow_html=True)

st.divider()

# ── Panel 1: Adoption Trajectory ─────────────────────────────────────────────
st.subheader("Panel 1: Adoption Trajectory")
client_df = client_dau_breakdown(activity_df)
if not client_df.empty:
    st.plotly_chart(adoption_area_chart(client_df), use_container_width=True)

    # WAU/MAU side metrics
    if not activity_df.empty and "weekly_active_users" in activity_df.columns:
        latest = activity_df.iloc[-1]
        wau = int(latest.get("weekly_active_users", 0))
        mau = int(latest.get("monthly_active_users", 0))
        cols = st.columns(2)
        with cols[0]:
            st.metric("WAU (trailing 7d)", f"{wau:,}")
        with cols[1]:
            st.metric("MAU (trailing 30d)", f"{mau:,}")
else:
    st.info("No adoption data for this range.")

st.divider()

# ── Panel 2: Output Amplification ────────────────────────────────────────────
st.subheader("Panel 2: Output Amplification")
if not prod_df.empty:
    st.plotly_chart(output_amplification_chart(prod_df), use_container_width=True)

    lang_df = top_languages(prod_df, n=5)
    if not lang_df.empty:
        st.plotly_chart(top_languages_chart(lang_df), use_container_width=True)
else:
    st.info("No productivity data for this range.")

st.divider()

# ── Panel 3: Human Attention Reclaimed ─────────────────────────────────────
st.subheader("Panel 3: Human Attention Reclaimed")
if not tools_df.empty:
    st.plotly_chart(autonomy_chart(tools_df), use_container_width=True)

    dist = delegation_distribution(tools_df)
    if dist:
        hands_off = hands_off_share(tools_df)
        cols = st.columns([2, 1])
        with cols[0]:
            st.plotly_chart(delegation_donut(dist), use_container_width=True)
        with cols[1]:
            st.metric("Hands-Off Share", f"{hands_off:.1f}%", help="Auto-high + Auto-medium delegation levels")
else:
    st.info("No tools/autonomy data for this range.")

st.divider()

# ── Power User Leaderboard ──────────────────────────────────────────────────
st.subheader("🏆 Power User Leaderboard")
st.caption(
    "Top 10 users ranked by tool calls across the selected range. "
    "Per-user PR counts aren't exposed by the Analytics API, so tool calls "
    "serve as the closest output proxy. Autonomy and delegation are surfaced "
    "alongside to identify true power users."
)

with st.spinner("Fetching per-user metrics..."):
    users_raw = fetch_users(start_date=start_str, end_date=end_str, limit=100)

if users_raw.get("_error"):
    st.warning(f"Could not load /users data: {users_raw['_error']}")
else:
    users_df = build_users_df(users_raw)
    leaderboard = power_user_leaderboard(users_df, n=10)

    if leaderboard.empty:
        st.info("No per-user activity in this range.")
    else:
        display_cols = {
            "rank": st.column_config.NumberColumn("Rank", width="small"),
        }
        label_col = "user_email" if "user_email" in leaderboard.columns else "user_id"
        display_cols[label_col] = st.column_config.TextColumn("User")
        if "tool_calls" in leaderboard.columns:
            display_cols["tool_calls"] = st.column_config.NumberColumn(
                "Tool Calls", format="%d"
            )
        if "billable_tokens" in leaderboard.columns:
            display_cols["billable_tokens"] = st.column_config.NumberColumn(
                "Credits (FSC)", format="%d"
            )
        if "sessions" in leaderboard.columns:
            display_cols["sessions"] = st.column_config.NumberColumn(
                "Sessions", format="%d"
            )
        if "autonomy_ratio" in leaderboard.columns:
            display_cols["autonomy_ratio"] = st.column_config.NumberColumn(
                "Autonomy Ratio", format="%.2f"
            )
        if "delegation_level" in leaderboard.columns:
            display_cols["delegation_level"] = st.column_config.TextColumn(
                "Delegation"
            )
        if "primary_model" in leaderboard.columns:
            display_cols["primary_model"] = st.column_config.TextColumn(
                "Primary Model"
            )
        if "languages" in leaderboard.columns:
            display_cols["languages"] = st.column_config.TextColumn("Top Languages")

        ordered = [c for c in [
            "rank",
            label_col,
            "tool_calls",
            "billable_tokens",
            "sessions",
            "autonomy_ratio",
            "delegation_level",
            "primary_model",
            "languages",
        ] if c in leaderboard.columns]

        st.dataframe(
            leaderboard[ordered],
            column_config=display_cols,
            hide_index=True,
            use_container_width=True,
        )

        if "autonomy_ratio" in leaderboard.columns and "tool_calls" in leaderboard.columns:
            top = leaderboard.iloc[0]
            st.caption(
                f"**#1 {top[label_col]}** drove {int(top['tool_calls']):,} tool calls "
                f"with autonomy ratio {top['autonomy_ratio']:.2f}"
                + (
                    f" at `{top['delegation_level']}` delegation."
                    if "delegation_level" in leaderboard.columns and top.get("delegation_level")
                    else "."
                )
            )

st.divider()

# ── Killer Chart ─────────────────────────────────────────────────────────────
st.subheader("The Killer Chart: Adoption + Autonomy + Output")
killer_fig = killer_chart(activity_df, tools_df, prod_df)
st.plotly_chart(killer_fig, use_container_width=True)

# Auto-generated caption
if not activity_df.empty and not tools_df.empty and not prod_df.empty:
    auto_trend = autonomy_trend_pct(tools_df)
    pr_trend = pr_velocity_change(prod_df)

    parts = []
    if auto_trend is not None:
        direction = "rose" if auto_trend > 0 else "fell"
        parts.append(f"autonomy ratio {direction} {abs(auto_trend):.1f}%")
    if pr_trend is not None:
        direction = "rose" if pr_trend > 0 else "fell"
        parts.append(f"PR output {direction} {abs(pr_trend):.1f}%")

    if parts:
        st.caption(f"**Trend summary:** Across this period, {' and '.join(parts)}.")

st.divider()
st.caption(f"Data range: {start_str} to {end_str}  •  Factory Analytics API v1")
