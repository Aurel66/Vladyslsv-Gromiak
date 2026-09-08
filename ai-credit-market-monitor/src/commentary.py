"""
Turns a flagged IssuerAssessment into prose for the morning credit note.

Two tiers:

  1. template_commentary()   Deterministic, rule-based sentence built
                              straight from the numbers. Always available,
                              zero dependencies, zero cost. This is what
                              outputs/sample_credit_morning_note.md was
                              generated with.

  2. ai_commentary()          Sends the same structured data to Claude
                               (via the Anthropic API) and asks it to write
                               the note the way a credit analyst would hand
                               it to a trader: tight, decision-relevant,
                               no fluff. Requires ANTHROPIC_API_KEY.

generate_commentary() tries the AI tier and falls back to the template tier
if no API key is configured or the call fails, so the tool never hard-fails
just because a key isn't set.
"""

from __future__ import annotations

import os

from src.credit_metrics import IssuerAssessment

SYSTEM_PROMPT = """You are a credit analyst supporting a Distribution & \
Credit Solutions trading desk. You are given structured credit metrics for \
one issuer, already flagged by a rules engine. Write a 2-4 sentence morning \
note a trader could read in 10 seconds: what changed, why it likely matters \
for spreads/liquidity, and what to watch next. Be concrete and quantitative. \
No disclaimers, no filler, no restating the numbers verbatim if prose \
already conveys the same point."""


def _user_prompt(a: IssuerAssessment) -> str:
    return (
        f"Issuer: {a.issuer} ({a.ticker}), sector {a.sector}, rating {a.rating}.\n"
        f"Leverage (Debt/EBITDA): {a.leverage}x\n"
        f"Interest coverage (EBIT/Interest): {a.interest_coverage}x\n"
        f"Latest spread: {a.latest_spread_bps:.0f}bps\n"
        f"5-day spread change: {a.spread_5d_change_bps:+.0f}bps\n"
        f"30-day spread change: {a.spread_30d_change_bps:+.0f}bps\n"
        f"Flags raised: {'; '.join(a.flags)}"
    )


def template_commentary(a: IssuerAssessment) -> str:
    move = "widened" if a.spread_5d_change_bps > 0 else "tightened"
    parts = [
        f"{a.issuer} ({a.rating}) is flagged {a.severity.lower()}: "
        f"leverage {a.leverage}x, interest coverage {a.interest_coverage}x."
    ]
    if abs(a.spread_5d_change_bps) >= 1:
        parts.append(
            f"Spreads have {move} {abs(a.spread_5d_change_bps):.0f}bps over the last 5 "
            f"sessions to {a.latest_spread_bps:.0f}bps."
        )
    parts.append("Recommend reviewing latest filings/news before the desk prices new risk.")
    return " ".join(parts)


def ai_commentary(a: IssuerAssessment, model: str = "claude-sonnet-4-5") -> str:
    from anthropic import Anthropic  # imported lazily so the sample/template
                                       # path has no hard dependency on it

    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(
        model=model,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(a)}],
    )
    return response.content[0].text.strip()


def generate_commentary(a: IssuerAssessment, use_ai: bool = True) -> tuple[str, str]:
    """Returns (text, source) where source is 'ai' or 'template'."""
    if use_ai and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ai_commentary(a), "ai"
        except Exception as exc:  # network/quota/model errors -> degrade, don't crash
            return f"{template_commentary(a)} [AI commentary unavailable: {exc}]", "template"
    return template_commentary(a), "template"
