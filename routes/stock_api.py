import yfinance as yf
from flask import Blueprint, jsonify, request

from config import PERIOD_MAP
from services.stocks import get_history, get_quote, parse_news

bp = Blueprint("stock_api", __name__, url_prefix="/api")


@bp.route("/stock/<ticker>")
def stock_quote(ticker):
    try:
        return jsonify(get_quote(ticker.upper()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/stock/<ticker>/history")
def stock_history(ticker):
    period = request.args.get("period", "1M")
    if period not in PERIOD_MAP:
        return jsonify({"error": f"Invalid period. Use: {', '.join(PERIOD_MAP)}"}), 400
    try:
        return jsonify(get_history(ticker.upper(), period))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/news/<ticker>")
def news(ticker):
    try:
        raw = yf.Ticker(ticker.upper()).news or []
        return jsonify(parse_news(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    try:
        results = yf.Search(q, max_results=6)
        out = [
            {"ticker": r.get("symbol", ""),
             "name": r.get("shortname") or r.get("longname") or r.get("symbol", "")}
            for r in (results.quotes or [])
            if r.get("symbol")
        ]
        return jsonify(out)
    except Exception:
        return jsonify([])
