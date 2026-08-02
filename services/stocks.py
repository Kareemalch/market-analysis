import pandas as pd
import yfinance as yf

from config import PERIOD_MAP

INCOME_STATEMENT_FIELDS = {
    "Total Revenue": "total_revenue",
    "Cost Of Revenue": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Operating Expense": "operating_expense",
    "Operating Income": "operating_income",
    "Net Income": "net_income",
}


def get_quote(ticker: str) -> dict:
    info = yf.Ticker(ticker).info

    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or price

    change = price - prev
    change_pct = (change / prev * 100) if prev else 0

    return {
        "ticker": ticker.upper(),
        "name": info.get("shortName") or info.get("longName") or ticker.upper(),
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "market_cap": info.get("marketCap"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "pe_ratio": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "week_high": info.get("fiftyTwoWeekHigh"),
        "week_low": info.get("fiftyTwoWeekLow"),
        "dividend": info.get("dividendYield"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "logo": info.get("logo_url"),
        "website": info.get("website"),
        "description": info.get("longBusinessSummary"),
    }


def get_history(ticker: str, period: str) -> list[dict]:
    p, interval = PERIOD_MAP.get(period, ("1mo", "1d"))

    hist = yf.Ticker(ticker).history(period=p, interval=interval)
    result = []
    for ts, row in hist.iterrows():
        label = ts.strftime("%H:%M") if period == "1D" else ts.strftime("%b %d")
        result.append({"date": label, "close": round(float(row["Close"]), 2)})
    return result


def get_income_statement(ticker: str) -> list[dict] | None:
    stmt = yf.Ticker(ticker).income_stmt
    if stmt is None or stmt.empty:
        return None

    periods = []
    for col in stmt.columns:
        row = {}
        has_data = False
        for label, key in INCOME_STATEMENT_FIELDS.items():
            val = stmt.at[label, col] if label in stmt.index else None
            if val is not None and not pd.isna(val):
                row[key] = round(float(val), 2)
                has_data = True
            else:
                row[key] = None
        if not has_data:
            continue
        row["period_end"] = col.strftime("%Y-%m-%d")
        periods.append(row)

    if not periods:
        return None

    periods.sort(key=lambda p: p["period_end"], reverse=True)
    return periods


def fmt_large(n) -> str:
    if n is None:
        return "N/A"
    if n >= 1e12:
        return f"${n / 1e12:.2f}T"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.2f}M"
    return f"${n:,.0f}"


def parse_news(raw: list) -> list[dict]:
    articles = []
    for item in raw[:8]:
        content = item.get("content") or item

        link = (
            (content.get("canonicalUrl") or {}).get("url")
            or content.get("link")
            or item.get("link")
            or "#"
        )

        pub_time = content.get("pubDate") or item.get("providerPublishTime")

        publisher = (
            (content.get("provider") or {}).get("displayName")
            or content.get("publisher")
            or item.get("publisher") or ""
        )

        articles.append({
            "title": content.get("title") or item.get("title"),
            "publisher": publisher,
            "link": link,
            "time": pub_time,
        })
    return articles
