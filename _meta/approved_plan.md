# Plan — Market Maker / Dealer-Flow Alpha Research

## Context

The user saw a popular claim ("MMs reverse-engineer to make retail follow the trend, then fade them") and wants to know:

1. **Theory** — what's actually real in market microstructure vs internet folklore
2. **Test** — actually run the testable signals on data, not vibes
3. **Retail playbook** — as a retail investor, what's borrowable / avoidable

The user is a Columbia MSBA student with quant + equity-research background. Treat them as technical. Working directory `/Users/luomengzhou/Documents/Market Maker/` is currently empty — green field.

**Honest framing for the deliverable** (this shapes the whole project): the meme version ("MMs deliberately trap retail") has zero peer-reviewed support. The *real* mechanisms behind the vibe are three boring-but-genuine things — PFOF/internalization economics, dealer gamma reflexivity, and retail attention bias — and only the latter two produce **testable** retail-side edges. The plan reflects this: we don't try to validate folklore, we build and test the real thing.

## Defaults baked in (override at approval)

| Decision | Default | Why |
|---|---|---|
| Universe | SPY/SPX primary, NVDA + TSLA as single-name case studies | Index = clean GEX mechanics; single names = louder retail/dealer dynamics for illustration |
| Data tier | Free + Columbia WRDS (assumed available — to verify) | Get to a real backtest without paid subscriptions; upgrade path noted |
| End use | Research + writeup, no live trading | Lowest risk, highest learning. Paper-trade phase can be added later |
| Depth | Multi-signal bake-off (4 signals) | Matches "test their strategy" without ballooning |

If any of those are wrong, flag at ExitPlanMode and I'll re-scope before implementation.

## Approach — three phases, three deliverables

### Phase 1 — Theory primer (markdown, ~3000 words)

**File:** `01_theory_primer.md`

**Structure:**
1. **The boring true answer to the meme** — PFOF economics (Citadel/Virtu profit from spread + adverse-selection sorting, not manipulation)
2. **The three real mechanisms** with citations:
   - PFOF & internalization (Battalio/Corwin/Jennings 2016, Boehmer-Jones-Zhang-Zhang 2021)
   - Dealer gamma/vanna/charm reflexivity (SpotGamma methodology, McElligott Nomura notes, Ni/Pearson/Poteshman 2005 pinning paper)
   - Retail attention bias (Barber & Odean 2008; recent 0DTE work)
3. **Folklore vs fact table** — explicit "what's real / what's meme" classification
4. **What's testable from this** → setup for Phase 2

**Important:** every citation gets verified via Google Scholar/SSRN search before going in the file. Phase-1 research-agent output had plausible-sounding but unverified attributions — those are starting points only, not facts to ship.

### Phase 2 — Signal construction & backtest

**Files:**
- `02_signals/gex.py` — dealer gamma exposure
- `02_signals/sentiment.py` — retail sentiment composite
- `02_signals/ats.py` — off-exchange volume tilt
- `02_signals/ofi.py` — order flow imbalance proxy
- `03_backtest.ipynb` — unified backtest, plots, tables
- `data/` — raw + cached parquet

**Four signals tested on SPY 2018–2025, daily horizon:**

| # | Signal | Data source (free path) | Data source (WRDS path) | Hypothesis |
|---|---|---|---|---|
| 1 | Dealer GEX regime | CBOE EOD chain CSV (free) | OptionMetrics IvyDB | Negative GEX → trend-follow regime; positive → mean-revert |
| 2 | Retail sentiment fade | StockTwits API + r/wallstreetbets ticker mentions | (same) | Extreme retail bullishness → forward 5-day fade |
| 3 | Off-exchange volume tilt | FINRA ATS weekly (T+2wk lag) | (same) | High dark-pool % = institutional accumulation phase |
| 4 | OFI proxy | Lee-Ready signing on yfinance daily OHLCV | TAQ tick-data signing (Boehmer 2021 algo) | Persistent buy imbalance → continuation |

**For each signal:**
- Construction with explicit lag/realism (T+2wk for FINRA, EOD for CBOE, etc.)
- Walk-forward in-sample (2018–2022) / out-of-sample (2023–2025) split
- Metrics: Sharpe, max DD, hit rate, turnover, capacity at $5k notional
- Transaction-cost model: 1 bp commission + half-spread slippage from yfinance OHLC
- Sanity baseline: random signal + buy-and-hold SPY, plotted alongside
- A unit test per signal with a known toy input (catches dumb bugs that ruin backtests)

**NVDA + TSLA case studies:** rerun signal #1 (GEX) and #2 (sentiment) on each, narrative writeup of one obvious episode (e.g., NVDA Q2-2024 earnings, GME 2021).

### Phase 3 — Retail playbook

**File:** `04_retail_playbook.md`

- What's actionable: GEX regime tilt for SPY exposure, sentiment fade as overlay, avoiding 0DTE pin levels at month-end
- What to skip: intraday OFI (wholesalers internalize before you see the print — Phase 2 backtest will likely confirm this is dead alpha for retail)
- Position sizing: half-Kelly on the OOS Sharpe, capped at 25% of NAV
- Implementation: which signal → which IBKR order type (regime tilt = SPY shares; sentiment fade = SPY puts)
- "When the model is wrong" — known regime-shift failure modes and the discretionary kill-switch

## Critical files (full paths)

```
/Users/luomengzhou/Documents/Market Maker/
├── 01_theory_primer.md
├── 02_signals/
│   ├── gex.py
│   ├── sentiment.py
│   ├── ats.py
│   └── ofi.py
├── 03_backtest.ipynb
├── 04_retail_playbook.md
├── data/
│   ├── raw/      # CBOE chains, FINRA ATS, StockTwits dumps
│   └── cache/    # parquet, deterministic
└── README.md     # navigation + reproduction steps
```

## Existing utilities / skills to reuse

- **`equity-research:initiate`** skill for the playbook formatting if we want a polished version
- **`anthropic-skills:luomeng-resume`** is unrelated — ignore
- **`data:write-query`** if we end up pulling WRDS via SQL
- **`finance:variance-analysis`** patterns for the backtest variance decomposition if needed
- Standard Python: `pandas`, `numpy`, `scipy.stats`, `matplotlib`, `yfinance`, `praw` (Reddit), `requests` (StockTwits)
- Optional: `vectorbt` or `bt` for backtest framework — but a hand-rolled loop is fine for daily horizon and clearer to read

## Open dependencies — confirm before Phase 2 starts

1. **WRDS access live?** If yes, signal #4 becomes a real Boehmer-style algorithm rather than Lee-Ready proxy. If no, we proceed with proxies and call out the gap honestly in the writeup.
2. **Data budget** — staying free-tier or willing to add Polygon ($150/mo) / Unusual Whales ($300/mo)? Free-tier is fully workable; paid tier mostly buys real-time, which is irrelevant for a research backtest.
3. **Forward / paper-trade phase?** — defaulted off. Easy to bolt on after Phase 2 if results are interesting.

## Verification

**Theory primer:**
- Every cited paper verified via Google Scholar before file ship — no hallucinated authors
- Spot-check: at least 3 citations from the writeup → resolve to a real DOI / SSRN ID

**Signal modules:**
- Unit test per signal with a synthetic toy input (e.g., a flat OI surface → GEX should be ~0)
- Replicate one published GEX figure from a SpotGamma blog post or a McElligott note for a known date — visual sanity check
- Sentiment: hand-label 50 StockTwits messages, compare to algorithm — accuracy ≥ 65% before using

**Backtest:**
- In-sample / OOS split is wall-clock, no leakage (signal at T uses only ≤T-1 data; FINRA T+2wk lag honored)
- Sharpe of buy-and-hold SPY benchmark printed alongside every strategy → no quietly underperforming the index
- Random-signal baseline produces ~0 Sharpe → confirms the framework isn't accidentally injecting alpha
- One backtest runs end-to-end from a clean checkout (`make all` or `python -m run_backtest`)

**Playbook:**
- Each recommendation traces back to a backtest result with a specific page/figure ref
- Implementation steps cross-checked against actual IBKR retail capabilities (e.g., 0DTE SPX option access, margin requirements)

## What this plan deliberately does NOT do

- No claim that we'll detect or prove "MM trap" behavior — there's no public data to even formulate that test
- No real-time / live-trading system — that's a separate project
- No HFT / sub-minute work — wholesaler internalization eats retail latency arb, by construction
- No options Greeks engine from scratch — we use Black-Scholes via `py_vollib` or pull pre-computed from CBOE/OptionMetrics
