#!/usr/bin/env python3
"""
generate_plots.py
-----------------
Generates one interactive Plotly HTML chart per year
(2024, 2025, 2026) for Bryan0324/oi-toi.

Each chart shows every contestant's cumulative global-best score
(sum of per-task best scores) over elapsed contest time.
Every submission / history record is rendered as a point on the line.

Usage
-----
    python3 tools/generate_plots.py [--top-n N] [--out-dir DIR]

Arguments
---------
    --top-n N       Highlight the top N finishers (default: 100).
                    Their lines are vivid and appear in the legend.
                    All other contestants are drawn as faint grey lines.
    --out-dir DIR   Output directory for HTML files (default: plots/).

Output
------
    <OUT_DIR>/plotly.min.js          (shared Plotly bundle, ~4.8 MB, written once)
    <OUT_DIR>/2024-TOI2024.html
    <OUT_DIR>/2025-TOI2025.html
    <OUT_DIR>/2026-TOI2026.html

Requirements
------------
    pip install plotly
"""

import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

from datetime import datetime, timezone

import plotly.graph_objects as go

# ─── Constants ───────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
YEARS = ["2024", "2025", "2026"]

# 20-colour palette (Tableau-20 approximation)
PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    "#499894", "#86bcb6", "#d37295", "#fabfd2", "#b6992d",
    "#f1ce63", "#a0cbe8", "#ffbe7d", "#8cd17d", "#79706e",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────
def fmt_elapsed(seconds: float) -> str:
    """Return a zero-padded HH:MM:SS string for *seconds* elapsed."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_ticks(duration_sec: int, n_ticks: int = 12):
    """Return evenly spaced tick values (seconds) and HH:MM:SS labels."""
    step = max(1, duration_sec // n_ticks)
    vals = list(range(0, duration_sec + 1, step))
    if vals[-1] != duration_sec:
        vals.append(duration_sec)
    labels = [fmt_elapsed(v) for v in vals]
    return vals, labels


# ─── Data Processing ─────────────────────────────────────────────────────────
def process_year(year: str, top_n: int):
    """
    Read ranking data for *year* and return a dict ready for chart building,
    or None if required files are missing.

    History format: [[user, task, unix_timestamp, score], ...]
    """
    rank_dir = REPO_ROOT / year / "ranking"
    contests_file = rank_dir / "contests" / "index.json"
    history_file = rank_dir / "history"

    if not contests_file.exists():
        print(f"  [{year}] Missing {contests_file}, skipping.", file=sys.stderr)
        return None
    if not history_file.exists():
        print(f"  [{year}] Missing {history_file}, skipping.", file=sys.stderr)
        return None

    contests = json.loads(contests_file.read_text(encoding="utf-8"))
    contest_key = next(iter(contests))
    contest = contests[contest_key]
    begin = contest["begin"]
    end = contest["end"]
    precision = contest.get("score_precision", 0)

    history = json.loads(history_file.read_text(encoding="utf-8"))

    # Keep only records inside the contest window, sorted by time
    records = sorted(
        (r for r in history if begin <= r[2] <= end),
        key=lambda r: r[2],
    )

    # Rolling per-task best → rolling global score per user
    user_task_best: dict[str, dict[str, float]] = {}
    user_points: dict[str, list[dict]] = {}

    for user, task, t, score in records:
        task_best = user_task_best.setdefault(user, {})
        if score > task_best.get(task, 0.0):
            task_best[task] = score

        global_score = sum(task_best.values())
        elapsed = t - begin

        user_points.setdefault(user, []).append(
            {"elapsed": elapsed, "global": global_score}
        )

    # Final global per user = last recorded global value
    final_global = {u: pts[-1]["global"] for u, pts in user_points.items()}

    # Sort users descending by final global score
    sorted_users = sorted(final_global, key=lambda u: final_global[u], reverse=True)
    top_users = set(sorted_users[:top_n])

    # Optional user display info (user_id → {f_name, l_name, team})
    users_file = rank_dir / "users" / "index.json"
    user_info: dict = {}
    if users_file.exists():
        user_info = json.loads(users_file.read_text(encoding="utf-8"))

    return {
        "year": year,
        "contest_key": contest_key,
        "contest_name": contest["name"],
        "begin": begin,
        "end": end,
        "precision": precision,
        "user_points": user_points,
        "sorted_users": sorted_users,
        "top_users": top_users,
        "user_info": user_info,
        "final_global": final_global,
    }


# ─── Chart Building ──────────────────────────────────────────────────────────
def build_figure(data: dict) -> go.Figure:
    contest_name = data["contest_name"]
    contest_key = data["contest_key"]
    begin = data["begin"]
    end = data["end"]
    precision = data["precision"]
    user_points = data["user_points"]
    sorted_users = data["sorted_users"]
    top_users = data["top_users"]
    user_info = data["user_info"]

    duration_sec = end - begin
    tickvals, ticktext = build_ticks(duration_sec, n_ticks=12)

    fig = go.Figure()

    top_list = [u for u in sorted_users if u in top_users]
    other_list = [u for u in sorted_users if u not in top_users]

    # ── Non-top users: faint grey, no legend ──────────────────────────────
    for user in other_list:
        pts = user_points[user]
        xs = [p["elapsed"] for p in pts]
        ys = [round(p["global"], precision) for p in pts]
        hover = [
            f"{user}<br>Time: {fmt_elapsed(p['elapsed'])}<br>"
            f"Global: {round(p['global'], precision)}"
            for p in pts
        ]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=user,
                showlegend=False,
                line=dict(color="rgba(160,160,160,0.18)", width=0.8),
                marker=dict(color="rgba(160,160,160,0.18)", size=3),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover,
            )
        )

    # ── Top-N users: vivid colours, shown in legend ───────────────────────
    rank_of = {u: i + 1 for i, u in enumerate(sorted_users)}
    for ci, user in enumerate(top_list):
        pts = user_points[user]
        rank = rank_of[user]
        info = user_info.get(user, {})
        # In users/index.json, "l_name" stores the school/affiliation (not a
        # surname) — e.g. {"f_name": "24T300", "l_name": "復旦高中", "team": null}
        school = info.get("l_name", "")
        label = f"#{rank} {user}" + (f" {school}" if school else "")

        xs = [p["elapsed"] for p in pts]
        ys = [round(p["global"], precision) for p in pts]
        hover = [
            f"<b>#{rank} {user}</b>"
            + (f" ({school})" if school else "")
            + f"<br>Time: {fmt_elapsed(p['elapsed'])}<br>"
            + f"Global: {round(p['global'], precision)}"
            for p in pts
        ]
        color = PALETTE[ci % len(PALETTE)]

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(color=color, size=5),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover,
            )
        )

    start_utc = datetime.fromtimestamp(begin, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    fig.update_layout(
        title=dict(
            text=f"{contest_name} — Global Score Progress",
            font=dict(size=20),
        ),
        xaxis=dict(
            title="Elapsed Time",
            tickvals=tickvals,
            ticktext=ticktext,
            range=[0, duration_sec],
            showgrid=True,
            gridcolor="#ececec",
        ),
        yaxis=dict(
            title="Global Score (cumulative best)",
            showgrid=True,
            gridcolor="#ececec",
        ),
        hovermode="closest",
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            xanchor="left",
            bgcolor="rgba(255,255,255,0.85)",
            font=dict(size=11),
        ),
        margin=dict(r=230, t=80, b=60, l=65),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f9f9f9",
        annotations=[
            dict(
                text=(
                    f"Contest: {contest_key} &nbsp;|&nbsp; "
                    f"Start: {start_utc} &nbsp;|&nbsp; "
                    f"Contestants: {len(sorted_users)} &nbsp;|&nbsp; "
                    f"Top highlighted: {len(top_users)}"
                ),
                xref="paper", yref="paper",
                x=0, y=1.055,
                showarrow=False,
                font=dict(size=11, color="#666"),
                align="left",
            )
        ],
    )
    return fig


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML score-progress charts for TOI rankings."
    )
    parser.add_argument(
        "--top-n", type=int, default=100, metavar="N",
        help="Highlight the top N finishers (default: 100).",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=REPO_ROOT / "plots", metavar="DIR",
        help="Output directory for HTML files (default: plots/).",
    )
    args = parser.parse_args()

    top_n: int = args.top_n
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== TOI Ranking Chart Generator ===")
    print(f"top-n   = {top_n}")
    print(f"out-dir = {out_dir}")

    generated = 0

    for year in YEARS:
        print(f"\n--- {year} ---")
        data = process_year(year, top_n)
        if data is None:
            continue

        print(f"  Contest : {data['contest_name']} ({data['contest_key']})")
        print(f"  Window  : {fmt_elapsed(0)} – {fmt_elapsed(data['end'] - data['begin'])}")
        print(f"  Users   : {len(data['sorted_users'])} with history entries")
        print(f"  Top N   : {len(data['top_users'])} highlighted")

        fig = build_figure(data)

        out_file = out_dir / f"{year}-{data['contest_key']}.html"
        # 'directory' mode: writes plotly.min.js once into out_dir and adds a
        # relative <script src="plotly.min.js"> tag to each HTML file.
        # All three HTML files share the same JS bundle (overwriting is harmless).
        fig.write_html(
            str(out_file),
            include_plotlyjs="directory",
            config=dict(
                responsive=True,
                scrollZoom=True,
                displaylogo=False,
                toImageButtonOptions=dict(format="png", filename=data["contest_key"]),
                modeBarButtonsToRemove=["select2d", "lasso2d"],
            ),
        )

        html_size = out_file.stat().st_size / 1024
        print(f"  Output  : {out_file} ({html_size:.0f} KB)")
        generated += 1

    js_path = out_dir / "plotly.min.js"
    if js_path.exists():
        js_size = js_path.stat().st_size / 1024
        print(f"\n  JS bundle: {js_path} ({js_size:.0f} KB, shared by all HTML files)")

    print(f"\n✓ Done — {generated} HTML file(s) written to {out_dir}")


if __name__ == "__main__":
    main()
