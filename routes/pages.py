import stripe
from flask import Blueprint, redirect, render_template, session, url_for

from auth import login_required
from config import FREE_WATCHLIST_LIMIT, INDICES, STRIPE_PRO_PRICE_ID
from extensions import supabase
from services.stocks import fmt_large, get_quote
from services.subscriptions import get_subscription, is_pro

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    indices = {}
    for name, sym in INDICES.items():
        try:
            indices[name] = get_quote(sym)
        except Exception:
            indices[name] = {"ticker": sym, "price": "—", "change_pct": 0}

    user_id = session.get("user_id")
    return render_template(
        "index.html",
        indices=indices,
        user=session.get("user_email"),
        pro=is_pro(user_id) if user_id else False,
    )


@bp.route("/stock/<ticker>")
def stock(ticker):
    ticker = ticker.upper()
    try:
        quote = get_quote(ticker)
    except Exception as e:
        return render_template("index.html", error=f"Could not load {ticker}: {e}",
                               indices={}, user=session.get("user_email"), pro=False)

    user_id = session.get("user_id")
    in_watchlist = False
    if user_id and supabase:
        res = (supabase.table("watchlist")
               .select("id")
               .eq("user_id", user_id)
               .eq("ticker", ticker)
               .execute())
        in_watchlist = bool(res.data)

    return render_template(
        "stock.html",
        quote=quote,
        ticker=ticker,
        fmt_large=fmt_large,
        in_watchlist=in_watchlist,
        user=session.get("user_email"),
        pro=is_pro(user_id) if user_id else False,
    )


@bp.route("/portfolio")
@login_required
def portfolio():
    user_id = session.get("user_id")
    return render_template(
        "portfolio.html",
        user=session.get("user_email"),
        pro=is_pro(user_id) if user_id else False,
        free_limit=FREE_WATCHLIST_LIMIT,
    )


@bp.route("/pricing")
def pricing():
    user_id = session.get("user_id")
    sub = get_subscription(user_id) if user_id else {"plan": "free", "status": "active"}
    return render_template(
        "pricing.html",
        user=session.get("user_email"),
        sub=sub,
        pro=sub.get("plan") == "pro" and sub.get("status") == "active",
        stripe_configured=bool(stripe.api_key and STRIPE_PRO_PRICE_ID),
    )


@bp.route("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("pages.index"))
    return render_template("auth.html")
