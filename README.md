# Lens

Shows a company's stock exposure across every fund run by a fictitious asset
manager ("Fenchurch Global Asset Management"), styled to match
[thegoldensource.com](https://www.thegoldensource.com)'s branding.

## Setup

```bash
python generate_data.py
```

Generates `data/holdings_monthly.csv`: 12 months of synthetic holdings for 4
funds drawn from a shared 42-company universe, with deliberate overlap (e.g.
Barclays sits in 3 of 4 funds, HSBC in all 4) so cross-fund exposure queries
are meaningful. Deterministic (fixed seed) — rerun any time to regenerate the
same data.

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

```json
{
  "company": {"name": "Barclays PLC", "ticker": "BARC.L", "sector": "Financials", "country": "UK"},
  "as_of_date": "2026-09-30",
  "total_market_value": 48123456.78,
  "total_funds_holding": 3,
  "total_funds_in_range": 4,
  "pct_of_manager_aum": 1.62,
  "avg_weight_pct": 4.1,
  "per_fund": [
    {"fund_id": "FGAM-FIN", "fund_name": "Fenchurch Financials Sector Fund", "market_value": 25500000.0, "weight_pct": 6.9, "rank_in_fund": 2},
    {"fund_id": "FGAM-UKI", "fund_name": "Fenchurch UK Equity Income Fund", "market_value": 15600000.0, "weight_pct": 7.2, "rank_in_fund": 1},
    {"fund_id": "FGAM-GEQ", "fund_name": "Fenchurch Global Equity Fund", "market_value": 7023456.78, "weight_pct": 0.9, "rank_in_fund": 14}
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
| `output/` | Generated dashboards (gitignored) |
