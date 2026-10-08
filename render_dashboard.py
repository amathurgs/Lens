"""Reports a company group's stock exposure across Fenchurch funds.

A "group" is a listed holdco (e.g. Barclays PLC) plus any opco subsidiaries that issue
their own bonds (e.g. Barclays Bank PLC), rolled up via the group_id column in the data.
Exposure is split into direct (equity/bond positions in the group itself) and indirect
(look-through exposure via ETF/index-fund positions whose constituents include the
group's equity).

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
ETF_CONSTITUENTS_CSV = BASE_DIR / "data" / "etf_constituents.csv"
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


def load_etf_constituents(path: Path = ETF_CONSTITUENTS_CSV) -> pd.DataFrame:
    if not path.exists():
        _fail(
            f"ETF constituents file not found at {path}. Run `python generate_data.py` first.",
        )
    return pd.read_csv(path)


def _group_display_name(df: pd.DataFrame, group_id: str) -> str:
    group_rows = df[df["group_id"] == group_id]
    equity_rows = group_rows[group_rows["asset_type"] == "equity"]
    if len(equity_rows):
        return str(equity_rows.iloc[0]["security_name"])
    return str(group_rows.iloc[0]["security_name"])


def _all_group_display_names(df: pd.DataFrame) -> list[str]:
    return sorted({_group_display_name(df, g) for g in df["group_id"].unique()})


def resolve_group(df: pd.DataFrame, query: str) -> tuple[str, str]:
    query_lower = query.strip().lower()
    securities = df[["security_id", "security_name", "group_id"]].drop_duplicates()

    substring_matches = securities[securities["security_name"].str.lower().str.contains(query_lower, regex=False)]
    distinct_groups = substring_matches["group_id"].unique().tolist()
    if len(distinct_groups) == 1:
        group_id = distinct_groups[0]
        return group_id, _group_display_name(df, group_id)
    if len(distinct_groups) > 1:
        suggestions = sorted({_group_display_name(df, g) for g in distinct_groups})
        _fail(f"'{query}' matches multiple companies, please be more specific.", suggestions)

    ticker_matches = securities[securities["security_id"].str.lower() == query_lower]
    distinct_groups = ticker_matches["group_id"].unique().tolist()
    if len(distinct_groups) == 1:
        group_id = distinct_groups[0]
        return group_id, _group_display_name(df, group_id)

    all_names = _all_group_display_names(df)
    close = difflib.get_close_matches(query, all_names, n=5, cutoff=0.5)
    if close:
        _fail(f"No company found matching '{query}'.", close)
    _fail(f"No company found matching '{query}'.", all_names)


def compute_exposure(df: pd.DataFrame, etf_df: pd.DataFrame, group_id: str, group_name: str) -> dict:
    as_of_date = df["snapshot_date"].max()
    snapshot = df[df["snapshot_date"] == as_of_date].copy()
    snapshot["rank_in_fund"] = (
        snapshot.groupby("fund_id")["weight_pct"].rank(ascending=False, method="min").astype(int)
    )

    all_funds = (
        snapshot[["fund_id", "fund_name", "fund_aum"]]
        .drop_duplicates()
        .set_index("fund_id")
    )

    group_rows = snapshot[snapshot["group_id"] == group_id]

    direct_by_fund: dict[str, float] = {}
    rank_by_fund: dict[str, int] = {}
    for fund_id, sub in group_rows.groupby("fund_id"):
        direct_by_fund[fund_id] = float(sub["market_value"].sum())
        rank_by_fund[fund_id] = int(sub["rank_in_fund"].min())

    by_entity = []
    for security_id, sub in group_rows.groupby("security_id"):
        by_entity.append(
            {
                "security_id": security_id,
                "entity_name": sub.iloc[0]["security_name"],
                "asset_type": sub.iloc[0]["asset_type"],
                "total_market_value": round(float(sub["market_value"].sum()), 2),
            }
        )
    by_entity.sort(key=lambda r: r["total_market_value"], reverse=True)

    equity_tickers = df[(df["group_id"] == group_id) & (df["asset_type"] == "equity")]["security_id"].unique().tolist()
    relevant_constituents = etf_df[etf_df["constituent_ticker"].isin(equity_tickers)]
    etf_weight: dict[str, float] = relevant_constituents.groupby("etf_security_id")["weight_pct"].sum().to_dict()

    etf_rows = snapshot[snapshot["security_id"].isin(etf_weight.keys())]
    indirect_by_fund: dict[str, float] = {}
    for fund_id, sub in etf_rows.groupby("fund_id"):
        value = sum(row["market_value"] * etf_weight[row["security_id"]] / 100 for _, row in sub.iterrows())
        indirect_by_fund[fund_id] = value

    per_fund = []
    for fund_id, fund_info in all_funds.iterrows():
        direct_mv = round(direct_by_fund.get(fund_id, 0.0), 2)
        indirect_mv = round(indirect_by_fund.get(fund_id, 0.0), 2)
        total_mv = round(direct_mv + indirect_mv, 2)
        fund_aum = float(fund_info["fund_aum"])
        per_fund.append(
            {
                "fund_id": fund_id,
                "fund_name": fund_info["fund_name"],
                "direct_market_value": direct_mv,
                "indirect_market_value": indirect_mv,
                "total_market_value": total_mv,
                "direct_weight_pct": round(direct_mv / fund_aum * 100, 2) if fund_aum else 0.0,
                "rank_in_fund": rank_by_fund.get(fund_id),
            }
        )
    per_fund.sort(key=lambda r: r["total_market_value"], reverse=True)

    total_direct_market_value = round(sum(r["direct_market_value"] for r in per_fund), 2)
    total_indirect_market_value = round(sum(r["indirect_market_value"] for r in per_fund), 2)
    total_market_value = round(total_direct_market_value + total_indirect_market_value, 2)
    total_funds_holding = sum(1 for r in per_fund if r["total_market_value"] > 0)
    total_manager_aum = float(all_funds["fund_aum"].sum())
    pct_of_manager_aum = round(total_market_value / total_manager_aum * 100, 2) if total_manager_aum else 0.0

    trend_rows = []
    for date in sorted(df["snapshot_date"].unique()):
        month_df = df[df["snapshot_date"] == date]
        direct = float(month_df[month_df["group_id"] == group_id]["market_value"].sum())
        month_etf_rows = month_df[month_df["security_id"].isin(etf_weight.keys())]
        indirect = float((month_etf_rows["market_value"] * month_etf_rows["security_id"].map(etf_weight) / 100).sum())
        trend_rows.append(
            {
                "month": pd.Timestamp(date).strftime("%Y-%m"),
                "total_market_value": round(direct + indirect, 2),
            }
        )

    return {
        "group": group_name,
        "as_of_date": pd.Timestamp(as_of_date).strftime("%Y-%m-%d"),
        "total_direct_market_value": total_direct_market_value,
        "total_indirect_market_value": total_indirect_market_value,
        "total_market_value": total_market_value,
        "total_funds_holding": total_funds_holding,
        "total_funds_in_range": len(all_funds),
        "pct_of_manager_aum": pct_of_manager_aum,
        "by_entity": by_entity,
        "per_fund": per_fund,
        "trend": trend_rows,
    }


def render_html(model: dict) -> str:
    group_name = html.escape(model["group"])
    entity_count = len(model["by_entity"])
    entity_word = "entity" if entity_count == 1 else "entities"

    not_held_banner = ""
    if model["total_funds_holding"] == 0:
        not_held_banner = (
            f'<div class="not-held-banner">{group_name} is not currently held, directly or '
            f"indirectly, by any Fenchurch fund as of {model['as_of_date']}.</div>"
        )

    kpi_cards = f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="value">{theme.format_compact_currency(model['total_market_value'])}</div>
        <div class="label">Total exposure</div>
      </div>
      <div class="kpi-card">
        <div class="value">{theme.format_compact_currency(model['total_direct_market_value'])}</div>
        <div class="label">Direct</div>
      </div>
      <div class="kpi-card">
        <div class="value">{theme.format_compact_currency(model['total_indirect_market_value'])}</div>
        <div class="label">Indirect (look-through)</div>
      </div>
      <div class="kpi-card">
        <div class="value">{model['total_funds_holding']} / {model['total_funds_in_range']}</div>
        <div class="label">Funds with exposure</div>
      </div>
      <div class="kpi-card">
        <div class="value">{model['pct_of_manager_aum']:.2f}%</div>
        <div class="label">% of manager AUM</div>
      </div>
    </div>
    """

    entity_rows = []
    for row in model["by_entity"]:
        entity_rows.append(
            f"""<tr>
              <td>{html.escape(row['entity_name'])}</td>
              <td><span class="badge">{html.escape(row['asset_type'])}</span></td>
              <td class="num">{theme.format_compact_currency(row['total_market_value'])}</td>
            </tr>"""
        )
    entity_table_html = f"""
    <div class="card">
      <h2>Direct holdings by entity</h2>
      <table id="entityTable">
        <thead>
          <tr>
            <th>Entity</th>
            <th>Asset type</th>
            <th class="num">Market value</th>
          </tr>
        </thead>
        <tbody>
          {''.join(entity_rows) if entity_rows else '<tr><td colspan="3">No direct holdings.</td></tr>'}
        </tbody>
      </table>
    </div>
    """

    fund_rows = []
    for row in model["per_fund"]:
        rank_display = row["rank_in_fund"] if row["rank_in_fund"] is not None else "—"
        fund_rows.append(
            f"""<tr>
              <td>{html.escape(row['fund_name'])}</td>
              <td class="num">{theme.format_compact_currency(row['direct_market_value'])}</td>
              <td class="num">{theme.format_compact_currency(row['indirect_market_value'])}</td>
              <td class="num">{theme.format_compact_currency(row['total_market_value'])}</td>
              <td class="num">{row['direct_weight_pct']:.2f}%</td>
              <td class="num">{rank_display}</td>
            </tr>"""
        )
    fund_table_html = f"""
    <div class="card">
      <h2>Per-fund breakdown</h2>
      <table id="fundTable">
        <thead>
          <tr>
            <th>Fund</th>
            <th class="num">Direct</th>
            <th class="num">Indirect</th>
            <th class="num">Total</th>
            <th class="num">Direct weight %</th>
            <th class="num">Rank in fund</th>
          </tr>
        </thead>
        <tbody>
          {''.join(fund_rows)}
        </tbody>
      </table>
    </div>
    """

    bar_config = json.dumps(theme.chartjs_stacked_bar_config(model["per_fund"])).replace("</", "<\\/")
    line_config = json.dumps(theme.chartjs_line_config(model["trend"])).replace("</", "<\\/")

    charts_html = f"""
    <div class="chart-row">
      <div class="card">
        <h2>Direct vs indirect exposure by fund</h2>
        <div class="chart-container"><canvas id="barChart"></canvas></div>
      </div>
      <div class="card">
        <h2>12-month exposure trend</h2>
        <div class="chart-container"><canvas id="lineChart"></canvas></div>
      </div>
    </div>
    """

    sort_script = """
    document.querySelectorAll('table thead').forEach((thead) => {
      Array.from(thead.querySelectorAll('th')).forEach((th, idx) => {
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
    });
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{group_name} — Exposure Dashboard | Lens</title>
{theme.GOOGLE_FONTS_LINK}
{theme.CHARTJS_CDN}
<style>{theme.build_page_css()}</style>
</head>
<body>
  <div class="hero">
    <p class="subtitle">Lens — Cross-Fund Exposure</p>
    <h1>{group_name}</h1>
    <p class="meta">{entity_count} {entity_word} held directly &middot; As of {model['as_of_date']}</p>
    <hr class="accent-bar">
  </div>
  <div class="wrap">
    {not_held_banner}
    {kpi_cards}
    {charts_html}
    {entity_table_html}
    {fund_table_html}
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


def write_html(html_text: str, group_name: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", group_name).strip("_")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{slug}_exposure_dashboard.html"
    out_path.write_text(html_text, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Report a company group's exposure across Fenchurch funds.")
    parser.add_argument("company", help="Company name or ticker, e.g. Barclays, HSBC (case-insensitive).")
    parser.add_argument("--open", action="store_true", help="Also open the generated HTML dashboard in a browser.")
    args = parser.parse_args(argv)

    print(f"Loading data from {DATA_CSV}...", file=sys.stderr)
    df = load_data()
    etf_df = load_etf_constituents()

    group_id, group_name = resolve_group(df, args.company)
    print(f"Resolved '{args.company}' -> group {group_name!r} ({group_id})", file=sys.stderr)

    model = compute_exposure(df, etf_df, group_id, group_name)

    html_text = render_html(model)
    out_path = write_html(html_text, group_name)
    print(f"Wrote dashboard to {out_path}", file=sys.stderr)

    result = {k: v for k, v in model.items() if k != "trend"}
    result["dashboard_path"] = str(out_path.resolve())

    print(json.dumps(result))

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
