"""Generates a deterministic dummy dataset of fund holdings for the Lens exposure demo.

Simulates a fictitious asset manager ("Fenchurch Global Asset Management") running 4 funds,
each holding securities drawn from a shared universe of equities, bonds and ETFs, over a
trailing 12-month window. Fund membership is explicitly authored (not randomly sampled) so
that cross-fund overlap for the demo's example companies (Barclays, HSBC, ...) is deliberate.

Barclays and HSBC are modelled as corporate groups: each holdco (Barclays PLC / HSBC Holdings
PLC) has opco subsidiaries that issue their own bonds (Barclays Bank PLC, HSBC Bank PLC, ...),
and both holdcos' equities also appear as constituents inside 2 of the 3 ETFs, giving indirect
look-through exposure on top of direct holdings.

Run this once to (re)create data/holdings_monthly.csv and data/etf_constituents.csv:
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
ETF_CONSTITUENTS_CSV = DATA_DIR / "etf_constituents.csv"

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

# entity_id -> (entity_name, entity_type, parent_entity_id or None)
ENTITIES = {
    "BARCLAYS_PLC": ("Barclays PLC", "holdco", None),
    "BARCLAYS_BANK_PLC": ("Barclays Bank PLC", "opco", "BARCLAYS_PLC"),
    "BARCLAYS_BANK_UK": ("Barclays Bank UK PLC", "opco", "BARCLAYS_PLC"),
    "HSBC_HOLDINGS": ("HSBC Holdings PLC", "holdco", None),
    "HSBC_BANK_PLC": ("HSBC Bank PLC", "opco", "HSBC_HOLDINGS"),
    "HSBC_UK_BANK": ("HSBC UK Bank PLC", "opco", "HSBC_HOLDINGS"),
    "HSBC_FRANCE": ("HSBC France", "opco", "HSBC_HOLDINGS"),
}


def ultimate_parent(entity_id: str) -> str:
    while ENTITIES[entity_id][2] is not None:
        entity_id = ENTITIES[entity_id][2]
    return entity_id


# ticker -> (company_name, sector, country, start_price, annual_drift, annual_vol)
EQUITIES = {
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

# listed equity ticker -> entity_id, only for tickers whose issuer is a modelled group holdco
GROUP_ISSUERS = {
    "BARC.L": "BARCLAYS_PLC",
    "HSBA.L": "HSBC_HOLDINGS",
}

# bond_id -> (name, sector, country, start_price, annual_drift, annual_vol, issuer_entity_id)
# near-par pricing, near-zero drift, low vol: bonds behave nothing like the equity GBM paths.
BONDS = {
    "BARC-BOND-1": ("Barclays Bank PLC 4.75% 2030", "Financials", "UK", 100.0, 0.0, 0.04, "BARCLAYS_BANK_PLC"),
    "BARC-BOND-2": ("Barclays Bank UK PLC 5.1% 2029", "Financials", "UK", 101.0, 0.0, 0.03, "BARCLAYS_BANK_UK"),
    "HSBC-BOND-1": ("HSBC Bank PLC 4.9% 2031", "Financials", "UK", 100.0, 0.0, 0.04, "HSBC_BANK_PLC"),
    "HSBC-BOND-2": ("HSBC UK Bank PLC 5.0% 2028", "Financials", "UK", 101.0, 0.0, 0.03, "HSBC_UK_BANK"),
    "HSBC-BOND-3": ("HSBC France 4.6% 2030", "Financials", "France", 99.5, 0.0, 0.05, "HSBC_FRANCE"),
}

# etf_id -> (name, sector, country, start_price, annual_drift, annual_vol)
ETFS = {
    "ISF.L": ("iShares FTSE 100 ETF", "Diversified", "UK", 750.0, 0.05, 0.12),
    "GFIN.L": ("Global Financials Index Fund", "Diversified", "Global", 500.0, 0.05, 0.14),
    "GEQ.L": ("Global Equity Index Fund", "Diversified", "Global", 600.0, 0.07, 0.16),
}

# etf_id -> [(constituent_ticker, weight_pct), ...] - static, not time-varying.
# Weights need not sum to 100: unmodelled residual constituents are expected.
ETF_CONSTITUENTS = {
    "ISF.L": [
        ("BARC.L", 2.1), ("HSBA.L", 3.4), ("LLOY.L", 1.8), ("NWG.L", 1.1), ("STAN.L", 1.0),
        ("SHEL", 8.2), ("BP", 4.1), ("ULVR", 3.6), ("DGE", 2.4), ("AZN", 7.8), ("GSK", 2.9),
        ("NG.L", 1.3), ("VOD.L", 1.6), ("LGEN.L", 0.9), ("PRU.L", 1.2), ("RR.L", 1.5), ("BA.L", 1.4),
    ],
    "GFIN.L": [
        ("BARC.L", 7.5), ("HSBA.L", 9.2), ("JPM", 11.0), ("GS", 8.3), ("MS", 6.1), ("C", 5.4),
        ("DBK.DE", 4.2), ("BNP.PA", 4.8), ("SAN.MC", 3.9), ("UBSG.SW", 4.5), ("STAN.L", 3.1),
        ("LLOY.L", 2.8), ("NWG.L", 2.2),
    ],
    "GEQ.L": [
        ("AAPL", 6.1), ("MSFT", 5.8), ("GOOGL", 4.2), ("JNJ", 2.9), ("PG", 2.3), ("KO", 1.9),
        ("CAT", 1.7), ("SIE", 1.4), ("NESN", 1.3), ("ROG", 1.1),
    ],
}


def build_securities() -> dict:
    securities = {}
    for ticker, (name, sector, country, price, drift, vol) in EQUITIES.items():
        securities[ticker] = {
            "name": name, "sector": sector, "country": country,
            "start_price": price, "annual_drift": drift, "annual_vol": vol,
            "asset_type": "equity", "issuer_entity_id": GROUP_ISSUERS.get(ticker),
        }
    for bond_id, (name, sector, country, price, drift, vol, issuer_entity_id) in BONDS.items():
        securities[bond_id] = {
            "name": name, "sector": sector, "country": country,
            "start_price": price, "annual_drift": drift, "annual_vol": vol,
            "asset_type": "bond", "issuer_entity_id": issuer_entity_id,
        }
    for etf_id, (name, sector, country, price, drift, vol) in ETFS.items():
        securities[etf_id] = {
            "name": name, "sector": sector, "country": country,
            "start_price": price, "annual_drift": drift, "annual_vol": vol,
            "asset_type": "etf", "issuer_entity_id": None,
        }
    return securities


SECURITIES = build_securities()


def resolve_group_id(security_id: str) -> str:
    issuer_entity_id = SECURITIES[security_id]["issuer_entity_id"]
    if issuer_entity_id:
        return ultimate_parent(issuer_entity_id)
    return security_id


HOLDINGS_PLAN = {
    "FGAM-FIN": (
        [(t, "core") for t in ["BARC.L", "HSBA.L", "JPM", "GS", "BARC-BOND-1", "HSBC-BOND-1"]]
        + [(t, "standard") for t in ["LLOY.L", "NWG.L", "STAN.L", "DBK.DE", "BNP.PA", "SAN.MC", "C", "MS", "UBSG.SW", "LGEN.L", "PRU.L", "GFIN.L"]]
        + [(t, "satellite") for t in ["SHEL", "BP", "AAPL", "MSFT", "ULVR", "NESN", "SIE", "AZN", "CAT", "VOD.L"]]
    ),
    "FGAM-GEQ": (
        [(t, "core") for t in ["AAPL", "MSFT", "GOOGL"]]
        + [(t, "standard") for t in ["JNJ", "PG", "KO", "AZN", "SIE", "CAT", "NESN", "DGE", "ULVR", "SHEL", "TTE", "ROG", "SAP", "GEQ.L"]]
        + [(t, "satellite") for t in ["HSBA.L", "BARC.L", "JPM", "UBSG.SW", "SONY", "ASML", "VOD.L", "LGEN.L", "ISF.L"]]
    ),
    "FGAM-UKI": (
        [(t, "core") for t in ["BARC.L", "HSBA.L", "BARC-BOND-2", "ISF.L"]]
        + [(t, "standard") for t in ["LLOY.L", "NWG.L", "STAN.L", "SHEL", "BP", "ULVR", "DGE", "NG.L", "VOD.L", "AZN", "GSK", "LGEN.L", "PRU.L", "BA.L"]]
        + [(t, "satellite") for t in ["RR.L", "GOOGL", "MSFT", "JPM", "NESN", "SIE"]]
    ),
    "FGAM-BAL": (
        [(t, "standard") for t in ["AAPL", "MSFT", "JNJ", "PG", "CAT", "SIE", "DGE", "KO", "NESN", "AZN", "GOOGL", "ASML", "ROG", "NOVN", "MC", "HSBC-BOND-2", "GEQ.L"]]
        + [(t, "satellite") for t in ["JPM", "GS", "SHEL", "VOD.L", "GSK", "HSBA.L", "SONY", "XOM"]]
    ),
}


def simulate_price_paths(rng: np.random.Generator) -> pd.DataFrame:
    end_date = (pd.Timestamp.today().normalize() - pd.offsets.MonthEnd(1))
    dates = pd.date_range(end=end_date, periods=N_MONTHS, freq="ME")

    rows = []
    for security_id in sorted(SECURITIES):
        security = SECURITIES[security_id]
        price = security["start_price"]
        drift = security["annual_drift"]
        vol = security["annual_vol"]
        for date in dates:
            z = rng.standard_normal()
            price = price * np.exp((drift - 0.5 * vol**2) / 12 + vol / np.sqrt(12) * z)
            rows.append({"security_id": security_id, "snapshot_date": date, "price": round(price, 2)})
    return pd.DataFrame(rows)


def build_fund_holdings(price_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    price_lookup = price_df.set_index(["security_id", "snapshot_date"])["price"]
    dates = sorted(price_df["snapshot_date"].unique())

    rows = []
    for fund in FUNDS:
        fund_id = fund["fund_id"]
        for security_id, tier in HOLDINGS_PLAN[fund_id]:
            price_t0 = price_lookup[(security_id, dates[0])]
            shares = round(TIER_WEIGHT_PCT[tier] / 100 * AUM_TIER_TARGET[fund["aum_tier"]] / price_t0)
            for date in dates:
                shares = max(1, round(shares * (1 + rng.normal(0, 0.015))))
                price = price_lookup[(security_id, date)]
                rows.append(
                    {
                        "fund_id": fund_id,
                        "fund_name": fund["fund_name"],
                        "fund_strategy": fund["fund_strategy"],
                        "security_id": security_id,
                        "snapshot_date": date,
                        "shares_held": int(shares),
                        "price": price,
                        "market_value": round(shares * price, 2),
                    }
                )
    return pd.DataFrame(rows)


FUNDS = [
    {"fund_id": "FGAM-FIN", "fund_name": "Fenchurch Financials Sector Fund", "fund_strategy": "Financials Sector", "aum_tier": "medium"},
    {"fund_id": "FGAM-GEQ", "fund_name": "Fenchurch Global Equity Fund", "fund_strategy": "Global Equity", "aum_tier": "large"},
    {"fund_id": "FGAM-UKI", "fund_name": "Fenchurch UK Equity Income Fund", "fund_strategy": "UK Equity Income", "aum_tier": "small"},
    {"fund_id": "FGAM-BAL", "fund_name": "Fenchurch Balanced Growth Fund", "fund_strategy": "Balanced Growth", "aum_tier": "medium"},
]


def finalize_schema(long_df: pd.DataFrame) -> pd.DataFrame:
    long_df = long_df.copy()
    long_df["security_name"] = long_df["security_id"].map(lambda s: SECURITIES[s]["name"])
    long_df["asset_type"] = long_df["security_id"].map(lambda s: SECURITIES[s]["asset_type"])
    long_df["sector"] = long_df["security_id"].map(lambda s: SECURITIES[s]["sector"])
    long_df["country"] = long_df["security_id"].map(lambda s: SECURITIES[s]["country"])
    long_df["issuer_entity_id"] = long_df["security_id"].map(lambda s: SECURITIES[s]["issuer_entity_id"] or "")
    long_df["group_id"] = long_df["security_id"].map(resolve_group_id)
    long_df["asset_manager"] = ASSET_MANAGER

    fund_aum = long_df.groupby(["fund_id", "snapshot_date"])["market_value"].sum().rename("fund_aum")
    long_df = long_df.join(fund_aum, on=["fund_id", "snapshot_date"])
    long_df["weight_pct"] = (long_df["market_value"] / long_df["fund_aum"] * 100).round(4)
    long_df["fund_aum"] = long_df["fund_aum"].round(2)
    long_df["snapshot_date"] = long_df["snapshot_date"].dt.strftime("%Y-%m-%d")

    columns = [
        "snapshot_date", "asset_manager", "fund_id", "fund_name", "fund_strategy", "fund_aum",
        "security_id", "security_name", "asset_type", "sector", "country",
        "issuer_entity_id", "group_id",
        "shares_held", "price", "market_value", "weight_pct",
    ]
    return long_df[columns]


def write_etf_constituents() -> pd.DataFrame:
    rows = []
    for etf_id, constituents in ETF_CONSTITUENTS.items():
        etf_name = SECURITIES[etf_id]["name"]
        for constituent_ticker, weight_pct in constituents:
            rows.append(
                {
                    "etf_security_id": etf_id,
                    "etf_name": etf_name,
                    "constituent_ticker": constituent_ticker,
                    "weight_pct": weight_pct,
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(ETF_CONSTITUENTS_CSV, index=False)
    return df


def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    price_df = simulate_price_paths(rng)
    long_df = build_fund_holdings(price_df, rng)
    final_df = finalize_schema(long_df)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(OUTPUT_CSV, index=False)
    etf_df = write_etf_constituents()

    print(f"Wrote {len(final_df)} rows to {OUTPUT_CSV}")
    print(f"Funds: {final_df['fund_id'].nunique()} | Securities: {final_df['security_id'].nunique()} | Asset types: {sorted(final_df['asset_type'].unique())}")
    print(f"Date range: {final_df['snapshot_date'].min()} to {final_df['snapshot_date'].max()}")
    print(f"Wrote {len(etf_df)} rows to {ETF_CONSTITUENTS_CSV}")


if __name__ == "__main__":
    main()
