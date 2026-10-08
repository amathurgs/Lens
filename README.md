# Lens

Shows a company group's stock exposure — direct and indirect — across every
fund run by a fictitious asset manager ("Fenchurch Global Asset Management"),
styled to match [thegoldensource.com](https://www.thegoldensource.com)'s
branding.

A "group" is a listed holding company plus any subsidiary legal entities that
issue their own bonds (e.g. querying "Barclays" includes bonds issued by
Barclays Bank PLC and Barclays Bank UK PLC, not just Barclays PLC equity).
Exposure is split into:
- **Direct** — equity and bond positions in the group itself.
- **Indirect (look-through)** — exposure via ETF/index-fund positions whose
  constituents include the group's equity, weighted by the constituent's
  weight in that fund.

## Setup

```bash
python generate_data.py
```

Generates:
- `data/holdings_monthly.csv` — 12 months of synthetic holdings for 4 funds
  drawn from a shared universe of 42 equities, 5 bonds (Barclays/HSBC
  subsidiaries only) and 3 ETFs, with deliberate overlap (e.g. Barclays sits
  in 3 of 4 funds via equity and/or bonds, HSBC in all 4) so cross-fund
  exposure queries are meaningful.
- `data/etf_constituents.csv` — static look-through weights for each ETF's
  constituents, used to compute indirect exposure.

Deterministic (fixed seed) — rerun any time to regenerate the same data.

## Usage

```bash
python render_dashboard.py "Barclays"
python render_dashboard.py "HSBC" --open
```

- `company` — company name or ticker, case-insensitive, partial match okay.
- `--open` — also launch the generated HTML dashboard in a browser. Omit this
  for programmatic/agent use; the dashboard file is always written to
  `output/`, it just isn't opened unless asked.

## Agent integration

This script is designed to be shelled out to by an orchestrating agent (e.g.
one calling codex) in response to a prompt like *"what's Barclays' total
exposure across funds?"*. **Stdout always carries exactly one JSON document
and nothing else** — parse it directly, no exit-code branching needed. All
human-readable progress goes to stderr.

### Success

A query resolves to a company **group** — the holdco plus any subsidiary
entities that issue their own bonds. `by_entity` lists every entity held
directly; `per_fund` splits each fund's exposure into direct and indirect
(look-through via ETFs).

```json
{
  "group": "Barclays PLC",
  "as_of_date": "2026-09-30",
  "total_direct_market_value": 45483713.75,
  "total_indirect_market_value": 2639796.55,
  "total_market_value": 48123510.30,
  "total_funds_holding": 4,
  "total_funds_in_range": 4,
  "pct_of_manager_aum": 1.62,
  "by_entity": [
    {"security_id": "BARC.L", "entity_name": "Barclays PLC", "asset_type": "equity", "total_market_value": 40123456.78},
    {"security_id": "BARC-BOND-1", "entity_name": "Barclays Bank PLC 4.75% 2030", "asset_type": "bond", "total_market_value": 3200000.0},
    {"security_id": "BARC-BOND-2", "entity_name": "Barclays Bank UK PLC 5.1% 2029", "asset_type": "bond", "total_market_value": 2160256.97}
  ],
  "per_fund": [
    {"fund_id": "FGAM-FIN", "fund_name": "Fenchurch Financials Sector Fund", "direct_market_value": 25500000.0, "indirect_market_value": 1929703.0, "total_market_value": 27429703.0, "direct_weight_pct": 6.9, "rank_in_fund": 2},
    {"fund_id": "FGAM-UKI", "fund_name": "Fenchurch UK Equity Income Fund", "direct_market_value": 15600000.0, "indirect_market_value": 432208.4, "total_market_value": 16032208.4, "direct_weight_pct": 7.2, "rank_in_fund": 1},
    {"fund_id": "FGAM-GEQ", "fund_name": "Fenchurch Global Equity Fund", "direct_market_value": 4383713.75, "indirect_market_value": 277884.8, "total_market_value": 4661598.55, "direct_weight_pct": 0.9, "rank_in_fund": 14}
  ],
  "dashboard_path": "C:\\Goldensource\\AI\\Claude\\Lens\\output\\Barclays_PLC_exposure_dashboard.html"
}
```

### Failure (company not found/ambiguous, data missing)

Exit code 1, stdout:

```json
{"error": "No company found matching 'xyz123'.", "suggestions": ["Barclays PLC", "BNP Paribas SA", "..."]}
```

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Builds the synthetic dataset (`data/holdings_monthly.csv`) |
| `theme.py` | GoldenSource brand colors/fonts + Chart.js config builders |
| `render_dashboard.py` | CLI: company name in, JSON + HTML dashboard out |
| `data/holdings_monthly.csv` | Generated dataset (committed for a self-contained repo) |
| `data/etf_constituents.csv` | Static ETF/index-fund look-through weights (committed) |
| `output/` | Generated dashboards (gitignored) |
