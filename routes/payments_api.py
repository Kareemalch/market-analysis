import stripe
from flask import Blueprint, jsonify, request, session

from auth import login_required
from config import STRIPE_CANCEL_URL, STRIPE_PRO_PRICE_ID, STRIPE_SUCCESS_URL, STRIPE_WEBHOOK_SECRET
from extensions import supabase
from services.subscriptions import get_subscription, unix_to_iso, upsert_subscription

bp = Blueprint("payments_api", __name__, url_prefix="/api/payments")


@bp.route("/status")
@login_required
def status():
    return jsonify(get_subscription(session["user_id"]))


@bp.route("/create-checkout", methods=["POST"])
@login_required
def create_checkout():
    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 503
    if not STRIPE_PRO_PRICE_ID:
        return jsonify({"error": "No Pro price configured"}), 503

    user_id = session["user_id"]
    email = session.get("user_email", "")
    sub = get_subscription(user_id)

    customer_id = sub.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(email=email, metadata={"user_id": user_id})
        customer_id = customer.id
        upsert_subscription(user_id, {"stripe_customer_id": customer_id})

    try:
        checkout = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRO_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            metadata={"user_id": user_id},
        )
        return jsonify({"url": checkout.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/cancel", methods=["POST"])
@login_required
def cancel():
    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 503

    sub = get_subscription(session["user_id"])
    sub_id = sub.get("stripe_subscription_id")
    if not sub_id:
        return jsonify({"error": "No active subscription found"}), 404

    try:
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        upsert_subscription(session["user_id"], {"status": "canceling"})
        return jsonify({"ok": True, "message": "Subscription will cancel at end of billing period."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({"error": "Webhook secret not configured"}), 503

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("user_id")
        sub_id = obj.get("subscription")
        cust_id = obj.get("customer")
        if user_id and sub_id:
            stripe_sub = stripe.Subscription.retrieve(sub_id)
            upsert_subscription(user_id, {
                "plan": "pro",
                "status": stripe_sub.status,
                "stripe_customer_id": cust_id,
                "stripe_subscription_id": sub_id,
                "current_period_end": unix_to_iso(stripe_sub.current_period_end),
            })

    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = obj["id"]
        cust_id = obj.get("customer")
        if supabase and cust_id:
            rows = (supabase.table("subscriptions")
                    .select("user_id")
                    .eq("stripe_customer_id", cust_id)
                    .execute().data)
            if rows:
                user_id = rows[0]["user_id"]
                plan = "free" if etype == "customer.subscription.deleted" else "pro"
                status = obj.get("status", "canceled")
                upsert_subscription(user_id, {
                    "plan": plan,
                    "status": status,
                    "stripe_subscription_id": sub_id,
                    "current_period_end": unix_to_iso(obj.get("current_period_end")),
                })

    elif etype == "invoice.payment_failed":
        cust_id = obj.get("customer")
        if supabase and cust_id:
            rows = (supabase.table("subscriptions")
                    .select("user_id")
                    .eq("stripe_customer_id", cust_id)
                    .execute().data)
            if rows:
                upsert_subscription(rows[0]["user_id"], {"status": "past_due"})

    return jsonify({"ok": True})
