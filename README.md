# 📈 Market Cap

A Google Finance–style stock tracker built with Flask. Look up any ticker for live pricing and charts, read the news, save stocks to a personal watchlist, and get an AI-generated plain-language summary of a company's financials.

## ✨ Features

- 💹 **Live quotes & charts** — real-time pricing via Yahoo Finance, no API key needed
- 📰 **News** — latest headlines per ticker
- ⭐ **Watchlist** — save your favorite stocks, backed by Supabase Auth
- 🤖 **AI Business Insights** — Gemini reads the income statement and explains it in plain English
- 💳 **Pro subscriptions** — Stripe Checkout for upgraded plans

## 🛠️ Stack

- Flask + `yfinance`
- Supabase (Auth + Postgres)
- Stripe
- Google Gemini
- Vanilla JS + Chart.js

## 🚀 Getting started

```bash
cp .env.example .env      # fill in your keys
pip install -r requirements.txt
python app.py              # http://localhost:5000
```

Then run `schema.sql` once in the Supabase SQL editor to set up the database tables.

## 🔑 Environment variables

You'll need Supabase, Stripe, and Gemini keys — see `.env.example` for the full list.
# market-analysis
