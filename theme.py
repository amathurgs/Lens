"""GoldenSource brand constants and Chart.js config builders for Lens dashboards."""

NAVY = "#002151"
BODY_TEXT = "#282B3E"
GOLD = "#F4A811"
BLUE = "#0166FF"
WHITE = "#FFFFFF"
GRID_LINE = "#EDEDED"
ROW_STRIPE = "#FAFAFA"
CARD_BORDER = "#D3D3D3"
DIVIDER = "#CCCCCC"
CARD_TINT = "rgba(0,33,81,0.05)"
BLUE_WASH = "rgba(1,102,255,0.10)"

FONT_HEADING = '"Inter", -apple-system, "Segoe UI", sans-serif'
FONT_BODY = '"Lato", -apple-system, "Segoe UI", sans-serif'

GOOGLE_FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&'
    'family=Lato:wght@400;700&display=swap" rel="stylesheet">'
)

CHARTJS_CDN = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>'


def format_compact_currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.1f}K"
    return f"{sign}${value:.0f}"


def build_page_css() -> str:
    return f"""
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        font-family: {FONT_BODY};
        color: {BODY_TEXT};
        background: {WHITE};
    }}
    .hero {{
        background: {NAVY};
        color: {WHITE};
        padding: 64px 48px 48px;
    }}
    .hero .subtitle {{
        font-family: {FONT_BODY};
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: rgba(255,255,255,.72);
        margin: 0 0 8px;
    }}
    .hero h1 {{
        font-family: {FONT_HEADING};
        font-size: 56px;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
    }}
    .hero .meta {{
        font-size: 14px;
        color: rgba(255,255,255,.72);
        margin-top: 12px;
    }}
    .accent-bar {{
        width: 64px;
        height: 4px;
        background: {GOLD};
        margin-top: 20px;
        border: none;
    }}
    .wrap {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 40px 48px 64px;
    }}
    .kpi-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-top: -56px;
        margin-bottom: 32px;
    }}
    .kpi-card {{
        background: {WHITE};
        border: 1px solid {CARD_BORDER};
        border-top: 4px solid {GOLD};
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,33,81,.08);
        padding: 24px;
    }}
    .kpi-card .value {{
        font-family: {FONT_HEADING};
        font-size: 36px;
        font-weight: 700;
        color: {NAVY};
        line-height: 1.1;
    }}
    .kpi-card .label {{
        font-family: {FONT_BODY};
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: {BODY_TEXT};
        margin-top: 8px;
    }}
    .chart-row {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 32px;
    }}
    .card {{
        background: {WHITE};
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,33,81,.06);
        padding: 24px;
    }}
    .card h2 {{
        font-family: {FONT_HEADING};
        font-size: 18px;
        font-weight: 700;
        color: {NAVY};
        margin: 0 0 16px;
    }}
    .chart-container {{
        height: 320px;
        position: relative;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    table thead th {{
        background: {CARD_TINT};
        color: {NAVY};
        font-family: {FONT_BODY};
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .03em;
        text-align: left;
        padding: 12px 14px;
        cursor: pointer;
        user-select: none;
    }}
    table tbody td {{
        padding: 12px 14px;
        font-size: 14px;
        border-bottom: 1px solid {GRID_LINE};
    }}
    table tbody tr:nth-child(even) {{
        background: {ROW_STRIPE};
    }}
    table tbody tr:hover {{
        background: {BLUE_WASH};
    }}
    td.num, th.num {{
        font-variant-numeric: tabular-nums;
        text-align: right;
    }}
    .footer {{
        background: {NAVY};
        color: rgba(255,255,255,.7);
        font-family: {FONT_BODY};
        font-size: 12px;
        padding: 24px 48px;
        text-align: center;
    }}
    .footer a {{
        color: {GOLD};
        text-decoration: none;
    }}
    .not-held-banner {{
        background: {CARD_TINT};
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        padding: 20px 24px;
        color: {NAVY};
        font-weight: 700;
        margin-bottom: 32px;
    }}
    """


def chartjs_bar_config(fund_bar: list[dict]) -> dict:
    labels = [row["fund_name"] for row in fund_bar]
    data = [row["market_value"] for row in fund_bar]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Market value",
                    "data": data,
                    "backgroundColor": BLUE,
                    "borderRadius": 4,
                    "borderSkipped": False,
                    "maxBarThickness": 28,
                }
            ],
        },
        "options": {
            "indexAxis": "y",
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {
                    "backgroundColor": NAVY,
                    "titleFont": {"family": "Lato"},
                    "bodyFont": {"family": "Lato"},
                },
            },
            "scales": {
                "x": {
                    "title": {"display": True, "text": "Market value (USD)", "font": {"family": "Lato"}},
                    "grid": {"color": GRID_LINE},
                    "ticks": {"font": {"family": "Lato"}},
                },
                "y": {
                    "grid": {"display": False},
                    "ticks": {"font": {"family": "Lato", "weight": 700}, "color": NAVY},
                },
            },
        },
    }


def chartjs_line_config(trend: list[dict]) -> dict:
    labels = [row["month"] for row in trend]
    data = [row["total_market_value"] for row in trend]
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Total exposure",
                    "data": data,
                    "borderColor": BLUE,
                    "backgroundColor": BLUE_WASH,
                    "fill": True,
                    "borderWidth": 2,
                    "tension": 0.25,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "pointBackgroundColor": BLUE,
                    "pointBorderColor": WHITE,
                    "pointBorderWidth": 2,
                }
            ],
        },
        "options": {
            "maintainAspectRatio": False,
            "interaction": {"mode": "index", "intersect": False},
            "plugins": {
                "legend": {"display": False},
                "tooltip": {
                    "backgroundColor": NAVY,
                    "titleFont": {"family": "Lato"},
                    "bodyFont": {"family": "Lato"},
                },
            },
            "scales": {
                "x": {"grid": {"display": False}, "ticks": {"font": {"family": "Lato"}}},
                "y": {
                    "beginAtZero": False,
                    "grid": {"color": GRID_LINE},
                    "ticks": {"font": {"family": "Lato"}},
                },
            },
        },
    }
