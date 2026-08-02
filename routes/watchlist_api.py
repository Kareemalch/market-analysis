from flask import Blueprint, jsonify, request, session

from auth import login_required
from config import FREE_WATCHLIST_LIMIT
from extensions import supabase
from services.stocks import get_quote
from services.subscriptions import is_pro

bp = Blueprint("watchlist_api", __name__, url_prefix="/api/watchlist")


@bp.route("", methods=["GET"])
@login_required
def get_watchlist():
    if not supabase:
        return jsonify([])

    rows = (supabase.table("watchlist")
            .select("ticker, added_at")
            .eq("user_id", session["user_id"])
            .order("added_at", desc=True)
            .execute().data)

    quotes = []
    for row in rows:
        try:
            quotes.append(get_quote(row["ticker"]))
        except Exception:
            quotes.append({"ticker": row["ticker"], "name": row["ticker"],
                           "price": None, "change_pct": 0})
    return jsonify(quotes)


@bp.route("", methods=["POST"])
@login_required
def add_to_watchlist():
    if not supabase:
        return jsonify({"error": "Supabase not configured"}), 503

    user_id = session["user_id"]
    ticker = ((request.get_json() or {}).get("ticker") or "").upper().strip()
    if not ticker:
        return jsonify({"error": "ticker required"}), 400

    if not is_pro(user_id):
        count = len(supabase.table("watchlist")
                    .select("id")
                    .eq("user_id", user_id)
                    .execute().data)
        if count >= FREE_WATCHLIST_LIMIT:
            return jsonify({
                "error": f"Free plan limited to {FREE_WATCHLIST_LIMIT} stocks. Upgrade to Pro for unlimited.",
                "upgrade": True,
            }), 403

    try:
        supabase.table("watchlist").insert({"user_id": user_id, "ticker": ticker}).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/<ticker>", methods=["DELETE"])
@login_required
def remove_from_watchlist(ticker):
    if not supabase:
        return jsonify({"ok": True})

    (supabase.table("watchlist")
     .delete()
     .eq("user_id", session["user_id"])
     .eq("ticker", ticker.upper())
     .execute())
    return jsonify({"ok": True})
