from datetime import datetime, timezone

from extensions import supabase

DEFAULT_SUBSCRIPTION = {"plan": "free", "status": "active", "current_period_end": None}


def get_subscription(user_id: str) -> dict:
    if not supabase or not user_id:
        return DEFAULT_SUBSCRIPTION

    try:
        res = (supabase.table("subscriptions")
               .select("plan, status, current_period_end, stripe_customer_id, stripe_subscription_id")
               .eq("user_id", user_id)
               .maybe_single()
               .execute())
        return res.data or DEFAULT_SUBSCRIPTION
    except Exception:
        return DEFAULT_SUBSCRIPTION


def is_pro(user_id: str) -> bool:
    sub = get_subscription(user_id)
    return sub.get("plan") == "pro" and sub.get("status") == "active"


def upsert_subscription(user_id: str, data: dict):
    if not supabase:
        return
    supabase.table("subscriptions").upsert(
        {"user_id": user_id, **data},
        on_conflict="user_id"
    ).execute()


def unix_to_iso(unix_ts) -> str | None:
    if not unix_ts:
        return None
    return datetime.fromtimestamp(int(unix_ts), tz=timezone.utc).isoformat()
