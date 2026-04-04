"""
Charts Component - Plotly charts for algorithm comparison.
"""

from typing import List, Optional
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st


def render_time_chart(
    df: pd.DataFrame,
    title: str = "Execution Time Comparison",
) -> None:
    """
    Render grouped bar chart comparing execution times.
    
    Args:
        df: DataFrame with columns: algorithm, testcase, elapsed_seconds
        title: Chart title.
    """
    fig = px.bar(
        df,
        x="testcase",
        y="elapsed_seconds",
        color="algorithm",
        barmode="group",
        title=title,
        labels={
            "elapsed_seconds": "Time (seconds)",
            "testcase": "Test Case",
            "algorithm": "Algorithm",
        },
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_nodes_chart(
    df: pd.DataFrame,
    metric: str = "nodes_generated",
    title: Optional[str] = None,
) -> None:
    """
    Render grouped bar chart comparing node metrics.
    
    Args:
        df: DataFrame with columns: algorithm, testcase, and the metric column.
        metric: Column name for the metric to plot.
        title: Chart title (auto-generated if None).
    """
    if title is None:
        metric_labels = {
            "nodes_generated": "Nodes Generated",
            "nodes_expanded": "Nodes Expanded",
        }
        title = f"{metric_labels.get(metric, metric)} Comparison"
    
    fig = px.bar(
        df,
        x="testcase",
        y=metric,
        color="algorithm",
        barmode="group",
        title=title,
        labels={
            metric: metric.replace("_", " ").title(),
            "testcase": "Test Case",
            "algorithm": "Algorithm",
        },
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_success_rate_chart(
    df: pd.DataFrame,
    title: str = "Success Rate by Algorithm",
) -> None:
    """
    Render bar chart showing solve success rate per algorithm.
    
    Args:
        df: DataFrame with columns: algorithm, testcase, solved
        title: Chart title.
    """
    # Calculate success rate per algorithm
    success_df = df.groupby("algorithm").agg(
        total=("solved", "count"),
        solved=("solved", "sum"),
    ).reset_index()
    
    success_df["success_rate"] = (success_df["solved"] / success_df["total"] * 100).round(1)
    
    fig = px.bar(
        success_df,
        x="algorithm",
        y="success_rate",
        color="algorithm",
        title=title,
        labels={
            "success_rate": "Success Rate (%)",
            "algorithm": "Algorithm",
        },
        text="success_rate",
    )
    
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        yaxis_range=[0, 110],
        showlegend=False,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_constraint_checks_chart(
    df: pd.DataFrame,
    title: str = "Constraint Checks Distribution",
) -> None:
    """
    Render box plot comparing constraint check counts.
    
    Args:
        df: DataFrame with columns: algorithm, constraint_checks
        title: Chart title.
    """
    fig = px.box(
        df,
        x="algorithm",
        y="constraint_checks",
        color="algorithm",
        title=title,
        labels={
            "constraint_checks": "Constraint Checks",
            "algorithm": "Algorithm",
        },
    )
    
    fig.update_layout(showlegend=False)
    
    st.plotly_chart(fig, use_container_width=True)


def render_backtracks_chart(
    df: pd.DataFrame,
    title: str = "Backtracks by Test Case",
) -> None:
    """
    Render line chart showing backtracks across testcases.
    
    Args:
        df: DataFrame with columns: algorithm, testcase, backtracks
        title: Chart title.
    """
    fig = px.line(
        df,
        x="testcase",
        y="backtracks",
        color="algorithm",
        markers=True,
        title=title,
        labels={
            "backtracks": "Backtracks",
            "testcase": "Test Case",
            "algorithm": "Algorithm",
        },
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_summary_table(df: pd.DataFrame) -> None:
    """
    Render summary statistics table.
    
    Args:
        df: DataFrame with comparison results.
    """
    # Calculate aggregate statistics per algorithm
    summary = df.groupby("algorithm").agg(
        avg_time=("elapsed_seconds", "mean"),
        total_nodes=("nodes_generated", "sum"),
        success_rate=("solved", lambda x: f"{x.mean() * 100:.1f}%"),
        avg_backtracks=("backtracks", "mean"),
        avg_constraint_checks=("constraint_checks", "mean"),
    ).reset_index()
    
    summary.columns = [
        "Algorithm",
        "Avg Time (s)",
        "Total Nodes",
        "Success Rate",
        "Avg Backtracks",
        "Avg Constraint Checks",
    ]
    
    # Format numeric columns
    summary["Avg Time (s)"] = summary["Avg Time (s)"].apply(lambda x: f"{x:.4f}")
    summary["Total Nodes"] = summary["Total Nodes"].apply(lambda x: f"{x:,.0f}")
    summary["Avg Backtracks"] = summary["Avg Backtracks"].apply(lambda x: f"{x:.1f}")
    summary["Avg Constraint Checks"] = summary["Avg Constraint Checks"].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(summary, use_container_width=True, hide_index=True)


__all__ = [
    "render_time_chart",
    "render_nodes_chart",
    "render_success_rate_chart",
    "render_constraint_checks_chart",
    "render_backtracks_chart",
    "render_summary_table",
]
