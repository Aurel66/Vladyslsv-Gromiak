"""
CLI entrypoint: builds a Credit Morning Note from the issuer/spread universe.

Usage:
    python main.py                          # sample data, AI commentary if ANTHROPIC_API_KEY is set
    python main.py --no-ai                  # sample data, rule-based commentary only
    python main.py --out outputs/note.md    # custom output path
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.credit_metrics import assess_universe
from src.data_sources import load_sample_issuers, load_sample_spreads
from src.report import build_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an AI-assisted credit morning note.")
    parser.add_argument("--no-ai", action="store_true", help="Skip the Claude commentary layer even if a key is set.")
    parser.add_argument("--out", default="outputs/credit_morning_note.md", help="Output markdown path.")
    args = parser.parse_args()

    issuers = load_sample_issuers()
    spreads = load_sample_spreads()
    assessments = assess_universe(issuers, spreads)

    report = build_report(assessments, use_ai=not args.no_ai)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"Wrote {out_path} ({len(assessments)} issuers assessed, "
          f"{sum(a.is_flagged for a in assessments)} flagged)")


if __name__ == "__main__":
    main()
