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

**Open blockers as of 2026-04-28:** Need to confirm (a) WRDS access via Columbia, (b) willingness to spend $200–500/mo on Polygon/Unusual Whales, before Phase 2 implementation. Defaulted to free-tier-only path if both no.
