"""Assembles the flagged issuer assessments into a Markdown morning note."""

from __future__ import annotations

from datetime import date

from src.commentary import generate_commentary
from src.credit_metrics import IssuerAssessment

SEVERITY_ORDER = {"HIGH RISK": 0, "CAUTION": 1, "STABLE": 2}


def build_report(assessments: list[IssuerAssessment], use_ai: bool = True, run_date: date | None = None) -> str:
    run_date = run_date or date.today()
    flagged = sorted(
        [a for a in assessments if a.is_flagged],
        key=lambda a: SEVERITY_ORDER[a.severity],
    )
    stable = [a for a in assessments if not a.is_flagged]

    lines = [
        f"# Credit Morning Note — {run_date.isoformat()}",
        "",
        f"Universe: {len(assessments)} issuers | Flagged: {len(flagged)} | Stable: {len(stable)}",
        "",
        "> Sample/illustrative data — see data/sample_issuers.csv and data/sample_spreads.csv.",
        "",
        "## Watchlist",
        "",
        "| Issuer | Sector | Rating | Leverage | Coverage | Spread | 5d Δ | Severity |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in flagged:
        lines.append(
            f"| {a.issuer} ({a.ticker}) | {a.sector} | {a.rating} | {a.leverage}x | "
            f"{a.interest_coverage}x | {a.latest_spread_bps:.0f}bps | "
            f"{a.spread_5d_change_bps:+.0f}bps | **{a.severity}** |"
        )
    if not flagged:
        lines.append("| _No issuers flagged today_ | | | | | | | |")

    lines += ["", "## Detail", ""]
    for a in flagged:
        text, source = generate_commentary(a, use_ai=use_ai)
        tag = "AI-drafted" if source == "ai" else "rule-based"
        lines += [
            f"### {a.issuer} ({a.ticker}) — {a.severity}",
            f"*{tag} commentary*",
            "",
            text,
            "",
            f"Flags: {'; '.join(a.flags)}",
            "",
        ]

    lines += ["## Stable / no action", ""]
    for a in stable:
        lines.append(
            f"- {a.issuer} ({a.ticker}): leverage {a.leverage}x, coverage {a.interest_coverage}x, "
            f"spread {a.latest_spread_bps:.0f}bps ({a.spread_5d_change_bps:+.0f}bps 5d)"
        )

    return "\n".join(lines) + "\n"
