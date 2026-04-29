---
name: Market Maker / dealer-flow alpha project
description: Multi-phase research project under ~/Documents/Market Maker — theory primer, signal backtests, retail playbook on MM/dealer-flow alpha
type: project
originSessionId: 2a77f291-50b4-4cb7-8727-42ef5122d422
---
User is researching the popular claim "market makers reverse-engineer retail flow to make them follow trends, then fade them." Project structured in three phases:

1. **Phase 1 — Theory primer** (`01_theory_primer.md`): separates real microstructure mechanisms (PFOF/internalization, dealer gamma reflexivity, retail attention bias) from internet folklore. Citations verified live via Google Scholar before being included.
2. **Phase 2 — Signal backtest** (`02_signals/*.py`, `03_backtest.ipynb`): four signals tested on SPY 2018–2025 — GEX regime, retail sentiment fade, off-exchange volume tilt, OFI proxy. Plus NVDA/TSLA case studies.
3. **Phase 3 — Retail playbook** (`04_retail_playbook.md`): translates surviving signals into actionable retail rules.

**Why:** User wanted rigor over folklore — explicitly asked for theory → test → playbook ordering. Plan approved 2026-04-28.

**How to apply:** When user mentions this project, dealer gamma, GEX, retail flow, or follows up on signal backtests, this is the relevant context. Working dir is `/Users/luomengzhou/Documents/Market Maker/`. Approved plan lives at `/Users/luomengzhou/.claude/plans/destination-market-maker-federated-dewdrop.md`.

**Status 2026-04-28 end of session:** Phase 1, 2.1, 2.2, 2.3, and 3 all done on free-tier path (SqueezeMetrics public CSV + yfinance). Pushed to GitHub at https://github.com/RomieCU/market-maker-research (private repo). User's machine returns to company in ~20 days, so the GitHub copy is the canonical one going forward.

**Headline empirical findings:**
1. **GEX defensive-tilt rule on SPY works** (OOS Sharpe 0.82, MaxDD -22% vs SPY -34%). Retail-actionable signal #1.
2. **DIX retail-flow Q1→Q5 monotonic positive spread** (t-stat ~10) — falsifies "fade aggregate retail" meme.
3. **Barber-Odean single-name attention-fade FAILS** on both Phase 2.3 (2026-hindsight basket) AND Phase 2.3b (2019-vintage basket including BBBY). Extreme groups outperform with t=5.9 to 9.4 in the wrong direction. Survivorship-bias controlled and conclusion still holds.
3b. **Phase 2.3b discovered a 5-day weak fade in `abnvol > 2×`** (t=-2.4) before the 63d continuation flip. Liquidity-provider inventory normalization story. Possible Phase 2.4 micro-strategy.
4. **Net edge is at INDEX level (Rule #1 GEX tilt), not single-name level.** Rewritten Rule #2 says don't trade attention extremes systematically in either direction.

**Outstanding next steps from playbook §"What we did NOT test":** 2.3b (2019-vintage meme basket re-test), 2.4 (FINRA ATS tilt), 2.5 (per-ticker GEX), 3.1 (cross-sectional GEX), 3.2 (live-attention dashboard), 4.1 (paper-trade Rule #1 in IBKR for 4 weeks). 4.1 is the highest-value next move.
