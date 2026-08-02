from flask import Blueprint, jsonify, request

from services.insights import (
    InsightsNotConfiguredError,
    LLMGenerationError,
    NoIncomeStatementError,
    get_or_generate_insights,
)

bp = Blueprint("insights_api", __name__, url_prefix="/api/stock")


@bp.route("/<ticker>/insights", methods=["POST"])
def generate_insights(ticker):
    force = bool((request.get_json(silent=True) or {}).get("force"))
    try:
        return jsonify(get_or_generate_insights(ticker, force=force))
    except NoIncomeStatementError:
        return jsonify({"error": f"No income statement data is available for {ticker.upper()}."}), 422
    except InsightsNotConfiguredError:
        return jsonify({"error": "AI insights are not configured."}), 503
    except LLMGenerationError:
        return jsonify({"error": "Could not generate insights right now. Please try again shortly."}), 502
    except Exception:
        return jsonify({"error": "Something went wrong generating insights."}), 500
