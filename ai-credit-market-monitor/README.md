# AI-Assisted Credit Market Monitor

A small pipeline that does what a Credit Trading desk's morning triage
looks like: pull an issuer universe, compute standard credit metrics,
flag names whose risk profile or spreads have moved, and draft a short
analyst note per flagged name — optionally using Claude (Anthropic API)
to write the prose the way a human analyst would hand it to a trader.

## Why this exists

I'm applying to credit trading / markets graduate roles (this repo started
as prep for a Credit Trading Trainee application). Rather than a generic
"AI demo," I wanted something that mirrors the actual daily workflow those
roles describe: monitoring risk indicators, producing P&L/risk-adjacent
reporting, doing credit and financial analysis on companies, and being
comfortable with data/AI tooling. This is that, built end to end.

It reuses the same core pattern — pull data → compute metrics → flag
outliers → have an LLM draft the write-up — that I'm applying to other
finance domains too (reconciliation exception reporting, macro/crypto
research), so this is also the template for those.

## What it does

1. **Loads an issuer universe** — sector, rating, and balance-sheet
   fundamentals (Total Debt, EBITDA, EBIT, Interest Expense) — plus a daily
   credit spread history per issuer.
2. **Computes standard credit metrics**: leverage (Debt/EBITDA), interest
   coverage (EBIT/Interest), and 5-day/30-day spread moves.
3. **Flags issuers** against simple, transparent thresholds (see
   `src/credit_metrics.py`) into `STABLE` / `CAUTION` / `HIGH RISK` —
   deliberately rules-based and inspectable rather than a black-box model,
   since the point is to triage faster, not to replace judgement.
4. **Drafts a note per flagged issuer.** With `ANTHROPIC_API_KEY` set, this
   calls Claude to write 2-4 sentences a trader could read in ten seconds.
   Without a key, it falls back automatically to a deterministic rule-based
   sentence built from the same numbers — the pipeline never hard-fails
   just because a key isn't configured.
5. **Assembles a Markdown "Credit Morning Note"** — a watchlist table plus
   per-issuer detail, written to `outputs/`.

## Data

`data/sample_issuers.csv` and `data/sample_spreads.csv` are **synthetic,
illustrative data** (the spread history is a seeded random walk with two
deliberate stress/relief events written by `data/generate_sample_spreads.py`)
— not real-time market data, and not a claim about any real company's
actual financials. This exists so the tool runs and is demoable offline,
with no market data subscription or API key required.

`src/data_sources.py` also includes real connectors — `fetch_fred_series()`
(pulls public FRED series like the ICE BofA corporate/HY OAS indices as a
market backdrop, no key needed) and `fetch_yfinance_fundamentals()`
(best-effort balance-sheet data via yfinance) — as a starting point for
pointing the same pipeline at live data. Single-name bond/CDS spreads
aren't available from a free public source; a real desk would swap this
for a Bloomberg/ICE/Markit/Refinitiv feed.

## Running it

```bash
pip install -r requirements.txt

# Rule-based commentary only (no key needed)
python main.py --no-ai

# With Claude-drafted commentary
export ANTHROPIC_API_KEY=sk-...
python main.py

python -m pytest tests/ -v
```

Output lands in `outputs/credit_morning_note.md`. A pre-generated example
using the rule-based tier is committed at
[`outputs/sample_credit_morning_note.md`](outputs/sample_credit_morning_note.md).

## Example: AI-drafted vs. rule-based commentary

Rule-based (what's actually committed in `outputs/sample_credit_morning_note.md`,
since this repo was built in a sandbox without live API access):

> Aurora Cruise Lines (B+) is flagged high risk: leverage 9.79x, interest
> coverage 0.77x. Spreads have tightened 7bps over the last 5 sessions to
> 540bps. Recommend reviewing latest filings/news before the desk prices
> new risk.

Illustrative example of the AI-drafted equivalent (`ai_commentary()` in
`src/commentary.py`, run with a real `ANTHROPIC_API_KEY`):

> Aurora's coverage below 1x is the headline here — EBIT no longer covers
> interest expense, which is a going-concern-adjacent signal even before
> touching the balance sheet. The 5-day tightening is likely short covering
> rather than a fundamental improvement; I'd fade it and watch the next
> earnings print for a covenant discussion before adding risk.

## Project structure

```
ai-credit-market-monitor/
  data/                    sample CSVs + the generator script that made them
  src/
    data_sources.py        sample loaders + real FRED/yfinance connectors
    credit_metrics.py      leverage/coverage/spread-move calcs + flagging
    commentary.py          Claude integration + rule-based fallback
    report.py              assembles the Markdown note
  main.py                  CLI entrypoint
  tests/                   unit tests for the metric calculations
  outputs/                 generated notes (sample committed)
```

## Extending this

- Swap `load_sample_*()` for real feeds via `fetch_fred_series()` /
  `fetch_yfinance_fundamentals()`, or a proper vendor feed.
- Thresholds in `credit_metrics.py` are flat; a real version would set them
  per-sector and per-rating-band.
- `report.py` could target Slack/email delivery instead of a Markdown file
  for an actual morning-note workflow.
