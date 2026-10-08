"""Reports a company's stock exposure across Fenchurch funds.

Agent-callable CLI: prints exactly one JSON document to stdout (success or
{"error": ..., "suggestions": [...]} on failure) so a calling agent can parse
the result without touching exit codes or stray text. Human-readable status
goes to stderr. The full GoldenSource-themed HTML dashboard is always written
to disk; pass --open to also launch it in a browser.

Usage:
    python render_dashboard.py Barclays
    python render_dashboard.py HSBC --open
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

import pandas as pd

import theme

BASE_DIR = Path(__file__).parent
DATA_CSV = BASE_DIR / "data" / "holdings_monthly.csv"
OUTPUT_DIR = BASE_DIR / "output"


def _fail(error: str, suggestions: list[str] | None = None) -> None:
    print(json.dumps({"error": error, "suggestions": suggestions or []}))
    sys.exit(1)


def load_data(path: Path = DATA_CSV) -> pd.DataFrame:
    if not path.exists():
        _fail(
            f"Data file not found at {path}. Run `python generate_data.py` first.",
        )
    df = pd.read_csv(path, parse_dates=["snapshot_date"])
    return df


def resolve_company(df: pd.DataFrame, query: str) -> str:
    companies = sorted(df["company_name"].unique())
    query_lower = query.strip().lower()

    substring_matches = [c for c in companies if query_lower in c.lower()]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        _fail(
            f"'{query}' matches multiple companies, please be more specific.",
            substring_matches,
        )

    ticker_matches = [
        c for c in companies
        if df.loc[df["company_name"] == c, "ticker"].iloc[0].lower() == query_lower
    ]
    if len(ticker_matches) == 1:
        return ticker_matches[0]

    close = difflib.get_close_matches(query, companies, n=5, cutoff=0.5)
    if close:
        _fail(f"No company found matching '{query}'.", close)
    _fail(f"No company found matching '{query}'.", companies)


def compute_exposure(df: pd.DataFrame, company_name: str) -> dict:
    as_of_date = df["snapshot_date"].max()
    snapshot = df[df["snapshot_date"] == as_of_date].copy()

    snapshot["rank_in_fund"] = (
        snapshot.groupby("fund_id")["weight_pct"].rank(ascending=False, method="min").astype(int)
    )

    company_rows = snapshot[snapshot["company_name"] == company_name]
    company_meta = company_rows.iloc[0] if len(company_rows) else df[df["company_name"] == company_name].iloc[0]

    all_funds = (
        snapshot[["fund_id", "fund_name", "fund_aum"]]
        .drop_duplicates()
        .set_index("fund_id")
    )

    per_fund = []
    for fund_id, fund_info in all_funds.iterrows():
        held = company_rows[company_rows["fund_id"] == fund_id]
        if len(held):
            row = held.iloc[0]
            per_fund.append(
                {
                    "fund_id": fund_id,
                    "fund_name": row["fund_name"],
                    "market_value": round(float(row["market_value"]), 2),
                    "weight_pct": round(float(row["weight_pct"]), 2),
                    "rank_in_fund": int(row["rank_in_fund"]),
                }
            )
        else:
            per_fund.append(
                {
                    "fund_id": fund_id,
                    "fund_name": fund_info["fund_name"],
                    "market_value": 0.0,
                    "weight_pct": 0.0,
                    "rank_in_fund": None,
                }
            )
    per_fund.sort(key=lambda r: r["market_value"], reverse=True)

    total_market_value = sum(r["market_value"] for r in per_fund)
    total_funds_holding = sum(1 for r in per_fund if r["market_value"] > 0)
    total_manager_aum = all_funds["fund_aum"].sum()
    pct_of_manager_aum = round(total_market_value / total_manager_aum * 100, 2) if total_manager_aum else 0.0
    held_weights = [r["weight_pct"] for r in per_fund if r["market_value"] > 0]
    avg_weight_pct = round(sum(held_weights) / len(held_weights), 2) if held_weights else 0.0

    trend_rows = []
    for date in sorted(df["snapshot_date"].unique()):
        month_rows = df[(df["snapshot_date"] == date) & (df["company_name"] == company_name)]
        trend_rows.append(
            {
                "month": pd.Timestamp(date).strftime("%Y-%m"),
                "total_market_value": round(float(month_rows["market_value"].sum()), 2),
                "num_funds": int((month_rows["market_value"] > 0).sum()),
            }
        )

    fund_bar = [{"fund_name": r["fund_name"], "market_value": r["market_value"]} for r in per_fund]

    return {
        "company": {
            "name": company_name,
            "ticker": company_meta["ticker"],
            "sector": company_meta["sector"],
            "country": company_meta["country"],
        },
        "as_of_date": pd.Timestamp(as_of_date).strftime("%Y-%m-%d"),
        "total_market_value": round(total_market_value, 2),
        "total_funds_holding": total_funds_holding,
        "total_funds_in_range": len(all_funds),
        "pct_of_manager_aum": pct_of_manager_aum,
        "avg_weight_pct": avg_weight_pct,
        "per_fund": per_fund,
        "trend": trend_rows,
        "fund_bar": fund_bar,
    }


def render_html(model: dict) -> str:
    company = model["company"]
    company_name = html.escape(company["name"])
    ticker = html.escape(company["ticker"])
    sector = html.escape(company["sector"])
    country = html.escape(company["country"])

    not_held_banner = ""
    if model["total_funds_holding"] == 0:
        not_held_banner = (
            f'<div class="not-held-banner">{company_name} is not currently held by any '
            f"Fenchurch fund as of {model['as_of_date']}.</div>"
        )

    kpi_cards = f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="value">{theme.format_compact_currency(model['total_market_value'])}</div>
        <div class="label">Total market value</div>
      </div>
      <div class="kpi-card">
        <div class="value">{model['total_funds_holding']} / {model['total_funds_in_range']}</div>
        <div class="label">Funds holding this stock</div>
      </div>
      <div class="kpi-card">
        <div class="value">{model['pct_of_manager_aum']:.2f}%</div>
        <div class="label">% of manager AUM</div>
      </div>
      <div class="kpi-card">
        <div class="value">{model['avg_weight_pct']:.2f}%</div>
        <div class="label">Avg weight (held funds)</div>
      </div>
    </div>
    """

    table_rows = []
    for row in model["per_fund"]:
        rank_display = row["rank_in_fund"] if row["rank_in_fund"] is not None else "—"
        table_rows.append(
            f"""<tr>
              <td>{html.escape(row['fund_name'])}</td>
              <td class="num">{theme.format_compact_currency(row['market_value'])}</td>
              <td class="num">{row['weight_pct']:.2f}%</td>
              <td class="num">{rank_display}</td>
            </tr>"""
        )
    table_html = f"""
    <div class="card">
      <h2>Per-fund breakdown</h2>
      <table id="fundTable">
        <thead>
          <tr>
            <th>Fund</th>
            <th class="num">Market value</th>
            <th class="num">Weight %</th>
            <th class="num">Rank in fund</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </div>
    """

    bar_config = json.dumps(theme.chartjs_bar_config(model["fund_bar"])).replace("</", "<\\/")
    line_config = json.dumps(theme.chartjs_line_config(model["trend"])).replace("</", "<\\/")

    charts_html = f"""
    <div class="chart-row">
      <div class="card">
        <h2>Exposure by fund</h2>
        <div class="chart-container"><canvas id="barChart"></canvas></div>
      </div>
      <div class="card">
        <h2>12-month exposure trend</h2>
        <div class="chart-container"><canvas id="lineChart"></canvas></div>
      </div>
    </div>
    """

    sort_script = """
    document.querySelectorAll('#fundTable thead th').forEach((th, idx) => {
      let asc = true;
      th.addEventListener('click', () => {
        const tbody = th.closest('table').querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => {
          const av = a.children[idx].innerText.replace(/[^0-9.\\-]/g, '');
          const bv = b.children[idx].innerText.replace(/[^0-9.\\-]/g, '');
          const an = parseFloat(av), bn = parseFloat(bv);
          if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
          return asc
            ? a.children[idx].innerText.localeCompare(b.children[idx].innerText)
            : b.children[idx].innerText.localeCompare(a.children[idx].innerText);
        });
        rows.forEach(r => tbody.appendChild(r));
        asc = !asc;
      });
    });
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{company_name} — Exposure Dashboard | Lens</title>
{theme.GOOGLE_FONTS_LINK}
{theme.CHARTJS_CDN}
<style>{theme.build_page_css()}</style>
</head>
<body>
  <div class="hero">
    <p class="subtitle">Lens — Cross-Fund Exposure</p>
    <h1>{company_name}</h1>
    <p class="meta">{ticker} &middot; {sector} &middot; {country} &middot; As of {model['as_of_date']}</p>
    <hr class="accent-bar">
  </div>
  <div class="wrap">
    {not_held_banner}
    {kpi_cards}
    {charts_html}
    {table_html}
  </div>
  <div class="footer">
    Lens by <a href="https://www.thegoldensource.com">GoldenSource</a> &middot; Fenchurch Global Asset Management (demo data)
  </div>
  <script>
    new Chart(document.getElementById('barChart'), {bar_config});
    new Chart(document.getElementById('lineChart'), {line_config});
    {sort_script}
  </script>
</body>
</html>
"""


def write_html(html_text: str, company_name: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", company_name).strip("_")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{slug}_exposure_dashboard.html"
    out_path.write_text(html_text, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Report a company's exposure across Fenchurch funds.")
    parser.add_argument("company", help="Company name or ticker, e.g. Barclays, HSBC (case-insensitive).")
    parser.add_argument("--open", action="store_true", help="Also open the generated HTML dashboard in a browser.")
    args = parser.parse_args(argv)

    print(f"Loading data from {DATA_CSV}...", file=sys.stderr)
    df = load_data()

    company_name = resolve_company(df, args.company)
    print(f"Resolved '{args.company}' -> {company_name}", file=sys.stderr)

    model = compute_exposure(df, company_name)

    html_text = render_html(model)
    out_path = write_html(html_text, company_name)
    print(f"Wrote dashboard to {out_path}", file=sys.stderr)

    result = {k: v for k, v in model.items() if k not in ("trend", "fund_bar")}
    result["dashboard_path"] = str(out_path.resolve())

    print(json.dumps(result))

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
