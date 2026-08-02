from flask import Blueprint, jsonify, request, session

from extensions import supabase
from services.subscriptions import upsert_subscription

bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@bp.route("/signup", methods=["POST"])
def signup():
    if not supabase:
        return jsonify({"ok": False, "error": "Supabase not configured"}), 503

    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            session["user_id"] = res.user.id
            session["user_email"] = res.user.email
            upsert_subscription(res.user.id, {"plan": "free", "status": "active"})
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Signup failed — check your email for a confirmation link"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@bp.route("/login", methods=["POST"])
def login():
    if not supabase:
        return jsonify({"ok": False, "error": "Supabase not configured"}), 503

    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            session["user_id"] = res.user.id
            session["user_email"] = res.user.email
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 401


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})
