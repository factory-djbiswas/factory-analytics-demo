"""Plotly chart builders for the Factory Analytics demo."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def kpi_tile(title: str, value: str, delta: str | None = None, color: str = "#f27b2f") -> str:
    delta_html = f'<div style="font-size:0.85rem;color:#888;margin-top:4px;">{delta}</div>' if delta else ""
    return f"""
    <div style="background:#fff;border:1px solid #eee;border-radius:12px;padding:16px 20px;text-align:center;">
        <div style="font-size:0.85rem;color:#888;text-transform:uppercase;letter-spacing:0.5px;">{title}</div>
        <div style="font-size:2rem;font-weight:700;color:{color};margin-top:6px;">{value}</div>
        {delta_html}
    </div>
    """


def adoption_area_chart(client_df: pd.DataFrame) -> go.Figure:
    if client_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No activity data for this range")
        return fig

    fig = px.area(
        client_df,
        x="date",
        y="dau",
        color="client",
        title="Adoption Trajectory: DAU by Client Type",
        labels={"dau": "Daily Active Users", "date": "Date", "client": "Client"},
        color_discrete_map={
            "terminal-ui": "#f27b2f",
            "web": "#3b82f6",
            "non-interactive-cli": "#10b981",
        },
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def output_amplification_chart(prod_df: pd.DataFrame) -> go.Figure:
    if prod_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No productivity data for this range")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=prod_df["date"],
            y=prod_df["files_edited"],
            name="Files Edited",
            marker_color="#cbd5e1",
            opacity=0.8,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=prod_df["date"],
            y=prod_df["git_prs_created"],
            name="PRs Created",
            mode="lines+markers",
            line=dict(color="#f27b2f", width=3),
            marker=dict(size=8),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Output Amplification: Files Edited vs. PRs Created",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_yaxes(title_text="Files Edited", secondary_y=False)
    fig.update_yaxes(title_text="PRs Created", secondary_y=True)
    return fig


def top_languages_chart(lang_df: pd.DataFrame) -> go.Figure:
    if lang_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No language data available")
        return fig

    fig = px.bar(
        lang_df,
        y="language",
        x="count",
        orientation="h",
        title="Top Languages by File Operations",
        labels={"count": "Operations", "language": "Language"},
        color="count",
        color_continuous_scale=["#f27b2f", "#ff9c6e"],
    )
    fig.update_layout(
        yaxis=dict(categoryorder="total ascending"),
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig


def autonomy_chart(tools_df: pd.DataFrame) -> go.Figure:
    if tools_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No tools data for this range")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=tools_df["date"],
            y=tools_df["autonomy_ratio_avg"],
            name="Autonomy Ratio",
            mode="lines+markers",
            line=dict(color="#f27b2f", width=3),
            marker=dict(size=8),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=tools_df["date"],
            y=tools_df["user_turns_per_session_avg"],
            name="User Turns / Session",
            mode="lines+markers",
            line=dict(color="#3b82f6", width=3, dash="dash"),
            marker=dict(size=8),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Human Attention Reclaimed: Autonomy vs. Turns per Session",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_yaxes(title_text="Autonomy Ratio", secondary_y=False)
    fig.update_yaxes(title_text="User Turns / Session", secondary_y=True)
    return fig


def delegation_donut(dist: dict[str, float]) -> go.Figure:
    if not dist:
        fig = go.Figure()
        fig.update_layout(title="No delegation data available")
        return fig

    labels = list(dist.keys())
    values = list(dist.values())
    colors = {
        "auto_high": "#f27b2f",
        "auto_medium": "#ff9c6e",
        "auto_low": "#fcd34d",
        "spec": "#93c5fd",
        "manual": "#cbd5e1",
    }

    fig = go.Figure(
        data=go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker_colors=[colors.get(k, "#ccc") for k in labels],
            textinfo="label+percent",
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Delegation Level Distribution",
        annotations=[dict(text="Auto<br>Share", x=0.5, y=0.5, font_size=14, showarrow=False)],
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )
    return fig


def killer_chart(activity_df: pd.DataFrame, tools_df: pd.DataFrame, prod_df: pd.DataFrame) -> go.Figure:
    if activity_df.empty or tools_df.empty or prod_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Insufficient data for combined view")
        return fig

    merged = activity_df[["date", "daily_active_users"]].merge(
        tools_df[["date", "autonomy_ratio_avg"]], on="date", how="inner"
    ).merge(
        prod_df[["date", "git_prs_created"]], on="date", how="inner"
    )

    if merged.empty:
        fig = go.Figure()
        fig.update_layout(title="Date alignment mismatch across endpoints")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=merged["date"],
            y=merged["daily_active_users"],
            name="DAU",
            mode="lines+markers",
            line=dict(color="#3b82b6", width=2),
            marker=dict(size=6),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=merged["date"],
            y=merged["autonomy_ratio_avg"],
            name="Autonomy Ratio",
            mode="lines+markers",
            line=dict(color="#f27b2f", width=3),
            marker=dict(size=8, symbol="diamond"),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(
            x=merged["date"],
            y=merged["git_prs_created"],
            name="PRs Created",
            marker_color="rgba(203,213,225,0.6)",
            marker_line_color="rgba(203,213,225,1)",
            marker_line_width=1,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="The Killer Chart: Adoption + Autonomy + Output",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_yaxes(title_text="DAU / Autonomy Ratio", secondary_y=False)
    fig.update_yaxes(title_text="PRs Created", secondary_y=True)
    return fig
