"""Generates a deterministic dummy dataset of fund holdings for the Lens exposure demo.

Simulates a fictitious asset manager ("Fenchurch Global Asset Management") running 4 funds,
each holding 20-25 securities drawn from a shared 42-company universe, over a trailing
12-month window. Fund membership is explicitly authored (not randomly sampled) so that
cross-fund overlap for the demo's example companies (Barclays, HSBC, ...) is deliberate.

Run this once to (re)create data/holdings_monthly.csv:
    python generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED = 1337
ASSET_MANAGER = "Fenchurch Global Asset Management"
N_MONTHS = 12

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_CSV = DATA_DIR / "holdings_monthly.csv"

AUM_TIER_TARGET = {
    "large": 1_200_000_000.0,
    "medium": 650_000_000.0,
    "small": 280_000_000.0,
}
TIER_WEIGHT_PCT = {
    "core": 7.0,
    "standard": 3.5,
    "satellite": 1.0,
}

# ticker -> (company_name, sector, country, start_price, annual_drift, annual_vol)
COMPANIES = {
    # Financials
    "BARC.L": ("Barclays PLC", "Financials", "UK", 190.0, 0.04, 0.25),
    "HSBA.L": ("HSBC Holdings PLC", "Financials", "UK", 650.0, 0.04, 0.25),
    "LLOY.L": ("Lloyds Banking Group PLC", "Financials", "UK", 55.0, 0.04, 0.25),
    "NWG.L": ("NatWest Group PLC", "Financials", "UK", 330.0, 0.04, 0.25),
    "STAN.L": ("Standard Chartered PLC", "Financials", "UK", 780.0, 0.04, 0.25),
    "SAN.MC": ("Banco Santander SA", "Financials", "Spain", 4.20, 0.04, 0.25),
    "DBK.DE": ("Deutsche Bank AG", "Financials", "Germany", 15.80, 0.04, 0.25),
    "BNP.PA": ("BNP Paribas SA", "Financials", "France", 62.00, 0.04, 0.25),
    "JPM": ("JPMorgan Chase & Co", "Financials", "US", 205.00, 0.04, 0.25),
    "C": ("Citigroup Inc", "Financials", "US", 68.00, 0.04, 0.25),
    "GS": ("Goldman Sachs Group Inc", "Financials", "US", 460.00, 0.04, 0.25),
    "MS": ("Morgan Stanley", "Financials", "US", 100.00, 0.04, 0.25),
    "UBSG.SW": ("UBS Group AG", "Financials", "Switzerland", 27.50, 0.04, 0.25),
    # Tech
    "AAPL": ("Apple Inc", "Technology", "US", 190.0, 0.09, 0.30),
    "MSFT": ("Microsoft Corp", "Technology", "US", 420.0, 0.09, 0.30),
    "GOOGL": ("Alphabet Inc", "Technology", "US", 165.0, 0.09, 0.30),
    "SAP": ("SAP SE", "Technology", "Germany", 190.0, 0.09, 0.30),
    "ASML": ("ASML Holding NV", "Technology", "Netherlands", 850.0, 0.09, 0.30),
    "SONY": ("Sony Group Corp", "Technology", "Japan", 90.0, 0.09, 0.30),
    # Energy
    "SHEL": ("Shell PLC", "Energy", "UK", 27.0, 0.03, 0.28),
    "BP": ("BP PLC", "Energy", "UK", 4.80, 0.03, 0.28),
    "XOM": ("ExxonMobil Corp", "Energy", "US", 115.0, 0.03, 0.28),
    "TTE": ("TotalEnergies SE", "Energy", "France", 62.0, 0.03, 0.28),
    # Consumer
    "ULVR": ("Unilever PLC", "Consumer Staples", "UK", 44.0, 0.05, 0.18),
    "NESN": ("Nestle SA", "Consumer Staples", "Switzerland", 95.0, 0.05, 0.18),
    "DGE": ("Diageo PLC", "Consumer Staples", "UK", 27.0, 0.05, 0.18),
    "MC": ("LVMH", "Consumer Discretionary", "France", 650.0, 0.05, 0.18),
    "PG": ("Procter & Gamble Co", "Consumer Staples", "US", 165.0, 0.05, 0.18),
    "KO": ("Coca-Cola Co", "Consumer Staples", "US", 62.0, 0.05, 0.18),
    # Healthcare
    "AZN": ("AstraZeneca PLC", "Healthcare", "UK", 125.0, 0.06, 0.20),
    "GSK": ("GSK PLC", "Healthcare", "UK", 16.0, 0.06, 0.20),
    "NOVN": ("Novartis AG", "Healthcare", "Switzerland", 95.0, 0.06, 0.20),
    "JNJ": ("Johnson & Johnson", "Healthcare", "US", 150.0, 0.06, 0.20),
    "ROG": ("Roche Holding AG", "Healthcare", "Switzerland", 260.0, 0.06, 0.20),
    # Industrials
    "SIE": ("Siemens AG", "Industrials", "Germany", 180.0, 0.05, 0.22),
    "BA.L": ("BAE Systems PLC", "Industrials", "UK", 13.0, 0.05, 0.22),
    "RR.L": ("Rolls-Royce Holdings PLC", "Industrials", "UK", 5.50, 0.05, 0.22),
    "CAT": ("Caterpillar Inc", "Industrials", "US", 350.0, 0.05, 0.22),
    # Utilities / Telecom
    "NG.L": ("National Grid PLC", "Utilities", "UK", 10.50, 0.03, 0.15),
    "VOD.L": ("Vodafone Group PLC", "Telecommunications", "UK", 0.75, 0.03, 0.15),
    # Insurance
    "LGEN.L": ("Legal & General Group PLC", "Insurance", "UK", 2.40, 0.05, 0.22),
    "PRU.L": ("Prudential PLC", "Insurance", "UK", 7.50, 0.05, 0.22),
}

FUNDS = [
    {"fund_id": "FGAM-FIN", "fund_name": "Fenchurch Financials Sector Fund", "fund_strategy": "Financials Sector", "aum_tier": "medium"},
    {"fund_id": "FGAM-GEQ", "fund_name": "Fenchurch Global Equity Fund", "fund_strategy": "Global Equity", "aum_tier": "large"},
    {"fund_id": "FGAM-UKI", "fund_name": "Fenchurch UK Equity Income Fund", "fund_strategy": "UK Equity Income", "aum_tier": "small"},
    {"fund_id": "FGAM-BAL", "fund_name": "Fenchurch Balanced Growth Fund", "fund_strategy": "Balanced Growth", "aum_tier": "medium"},
]

HOLDINGS_PLAN = {
    "FGAM-FIN": (
        [(t, "core") for t in ["BARC.L", "HSBA.L", "JPM", "GS"]]
        + [(t, "standard") for t in ["LLOY.L", "NWG.L", "STAN.L", "DBK.DE", "BNP.PA", "SAN.MC", "C", "MS", "UBSG.SW", "LGEN.L", "PRU.L"]]
        + [(t, "satellite") for t in ["SHEL", "BP", "AAPL", "MSFT", "ULVR", "NESN", "SIE", "AZN", "CAT", "VOD.L"]]
    ),
    "FGAM-GEQ": (
        [(t, "core") for t in ["AAPL", "MSFT", "GOOGL"]]
        + [(t, "standard") for t in ["JNJ", "PG", "KO", "AZN", "SIE", "CAT", "NESN", "DGE", "ULVR", "SHEL", "TTE", "ROG", "SAP"]]
        + [(t, "satellite") for t in ["HSBA.L", "BARC.L", "JPM", "UBSG.SW", "SONY", "ASML", "VOD.L", "LGEN.L"]]
    ),
    "FGAM-UKI": (
        [(t, "core") for t in ["BARC.L", "HSBA.L"]]
        + [(t, "standard") for t in ["LLOY.L", "NWG.L", "STAN.L", "SHEL", "BP", "ULVR", "DGE", "NG.L", "VOD.L", "AZN", "GSK", "LGEN.L", "PRU.L", "BA.L"]]
        + [(t, "satellite") for t in ["RR.L", "GOOGL", "MSFT", "JPM", "NESN", "SIE"]]
    ),
    "FGAM-BAL": (
        [(t, "standard") for t in ["AAPL", "MSFT", "JNJ", "PG", "CAT", "SIE", "DGE", "KO", "NESN", "AZN", "GOOGL", "ASML", "ROG", "NOVN", "MC"]]
        + [(t, "satellite") for t in ["JPM", "GS", "SHEL", "VOD.L", "GSK", "HSBA.L", "SONY", "XOM"]]
    ),
}


def simulate_price_paths(rng: np.random.Generator) -> pd.DataFrame:
    end_date = (pd.Timestamp.today().normalize() - pd.offsets.MonthEnd(1))
    dates = pd.date_range(end=end_date, periods=N_MONTHS, freq="ME")

    rows = []
    for ticker in sorted(COMPANIES):
        _, _, _, start_price, drift, vol = COMPANIES[ticker]
        price = start_price
        for date in dates:
            z = rng.standard_normal()
            price = price * np.exp((drift - 0.5 * vol**2) / 12 + vol / np.sqrt(12) * z)
            rows.append({"ticker": ticker, "snapshot_date": date, "price": round(price, 2)})
    return pd.DataFrame(rows)


def build_fund_holdings(price_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    price_lookup = price_df.set_index(["ticker", "snapshot_date"])["price"]
    dates = sorted(price_df["snapshot_date"].unique())

    rows = []
    for fund in FUNDS:
        fund_id = fund["fund_id"]
        for ticker, tier in HOLDINGS_PLAN[fund_id]:
            price_t0 = price_lookup[(ticker, dates[0])]
            shares = round(TIER_WEIGHT_PCT[tier] / 100 * AUM_TIER_TARGET[fund["aum_tier"]] / price_t0)
            for date in dates:
                shares = max(1, round(shares * (1 + rng.normal(0, 0.015))))
                price = price_lookup[(ticker, date)]
                rows.append(
                    {
                        "fund_id": fund_id,
                        "fund_name": fund["fund_name"],
                        "fund_strategy": fund["fund_strategy"],
                        "ticker": ticker,
                        "snapshot_date": date,
                        "shares_held": int(shares),
                        "price": price,
                        "market_value": round(shares * price, 2),
                    }
                )
    return pd.DataFrame(rows)


def finalize_schema(long_df: pd.DataFrame) -> pd.DataFrame:
    long_df = long_df.copy()
    long_df["company_name"] = long_df["ticker"].map(lambda t: COMPANIES[t][0])
    long_df["sector"] = long_df["ticker"].map(lambda t: COMPANIES[t][1])
    long_df["country"] = long_df["ticker"].map(lambda t: COMPANIES[t][2])
    long_df["asset_manager"] = ASSET_MANAGER

    fund_aum = long_df.groupby(["fund_id", "snapshot_date"])["market_value"].sum().rename("fund_aum")
    long_df = long_df.join(fund_aum, on=["fund_id", "snapshot_date"])
    long_df["weight_pct"] = (long_df["market_value"] / long_df["fund_aum"] * 100).round(4)
    long_df["fund_aum"] = long_df["fund_aum"].round(2)
    long_df["snapshot_date"] = long_df["snapshot_date"].dt.strftime("%Y-%m-%d")

    columns = [
        "snapshot_date", "asset_manager", "fund_id", "fund_name", "fund_strategy", "fund_aum",
        "company_name", "ticker", "sector", "country", "shares_held", "price", "market_value", "weight_pct",
    ]
    return long_df[columns]


def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    price_df = simulate_price_paths(rng)
    long_df = build_fund_holdings(price_df, rng)
    final_df = finalize_schema(long_df)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Wrote {len(final_df)} rows to {OUTPUT_CSV}")
    print(f"Funds: {final_df['fund_id'].nunique()} | Companies: {final_df['company_name'].nunique()}")
    print(f"Date range: {final_df['snapshot_date'].min()} to {final_df['snapshot_date'].max()}")


if __name__ == "__main__":
    main()
