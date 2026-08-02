import json
from datetime import datetime, timedelta, timezone
from typing import Literal

import groq
from pydantic import BaseModel, Field

from config import GROQ_MODEL
from extensions import groq_client, supabase
from services.stocks import get_income_statement

INSIGHTS_CACHE_TTL = timedelta(hours=24)

SYSTEM_PROMPT = (
    "You are a financial analyst assistant that writes plain-language summaries of "
    "public companies for retail investors using a stock tracking app. You will be given "
    "a company's ticker symbol and its annual income statement line items for up to five "
    "recent fiscal years, most recent first.\n\n"
    "Write in clear, jargon-free language a non-expert investor can understand. Do not "
    "restate the raw numbers as a list — explain what they mean and why they matter (for "
    "example, margin trends, cost pressure, growth or contraction). Base every statement "
    "strictly on the data provided. Never invent, estimate, or assume figures, forward "
    "guidance, or qualitative facts (product launches, management changes, competitive "
    "dynamics, etc.) that are not present in the data you were given. If the data is "
    "insufficient to support a claim, say so plainly rather than speculating.\n\n"
    "If only one fiscal period of data is provided, produce a single-period snapshot: "
    "describe the company's current financial position from that one year alone, and do "
    "not describe trends, direction, or comparisons across years — there is nothing to "
    "compare."
)

class BusinessInsights(BaseModel):
    business_overview: str = Field(
        description="1-2 sentences describing what the company does, based on its ticker/name and the data provided. Plain language, no jargon."
    )
    income_statement_summary: str = Field(
        description="A plain-language walkthrough of the income statement (2-5 sentences). Explain what the numbers mean and why -- margin trends, cost pressure, revenue growth or contraction -- not just a restatement of the figures. If only one period was provided, describe that single period's financial position instead of a trend."
    )
    performance_verdict: Literal["healthy", "improving", "declining", "mixed"] = Field(
        description="One-word verdict on overall financial performance based strictly on the provided data. Use 'improving' or 'declining' only when multiple periods are available to compare; with a single period, use 'healthy' or 'mixed'."
    )
    performance_drivers: list[str] = Field(
        description="1 to 3 short, specific factors supporting performance_verdict, each grounded in the provided data (e.g. 'Gross margin expanded from 41% to 44% over three years')."
    )
    notable_flags: list[str] = Field(
        description="Specific concerns visible in the data -- margin compression, an expense spike, a net loss, revenue decline. Empty list if nothing notable stands out. Do not pad this to seem thorough."
    )
    data_basis: Literal["single_period", "multi_period"] = Field(
        description="Whether this summary was generated from a single fiscal period or multiple periods -- must match the number of periods actually provided in the prompt."
    )


class InsightsError(Exception):
    pass


class NoIncomeStatementError(InsightsError):
    pass


class InsightsNotConfiguredError(InsightsError):
    pass


class LLMGenerationError(InsightsError):
    pass


def get_or_generate_insights(ticker: str, force: bool = False) -> dict:
    ticker = ticker.upper()
    cached = None if force else _fetch_cached(ticker)

    if cached and not _is_stale(cached["generated_at"]):
        return _to_response(cached, cached=True)

    if cached:
        periods = get_income_statement(ticker)
        if periods and periods[0]["period_end"] == cached.get("latest_fiscal_period_end"):
            return _to_response(cached, cached=True)
    else:
        periods = get_income_statement(ticker)

    if not periods:
        raise NoIncomeStatementError()

    summary = _call_llm(ticker, periods)
    record = _build_record(ticker, periods, summary)
    _upsert_cache(record)
    return _to_response(record, cached=False)


def _fmt(v):
    return "N/A" if v is None else f"{v:,.0f}"


def _build_user_prompt(ticker: str, periods: list[dict]) -> str:
    lines = [f"Ticker: {ticker}", "", "Annual income statement (most recent first, USD):"]
    for p in periods:
        lines.append(
            f"- Period ending {p['period_end']}: "
            f"Total Revenue={_fmt(p['total_revenue'])}, "
            f"Cost of Revenue={_fmt(p['cost_of_revenue'])}, "
            f"Gross Profit={_fmt(p['gross_profit'])}, "
            f"Operating Expense={_fmt(p['operating_expense'])}, "
            f"Operating Income={_fmt(p['operating_income'])}, "
            f"Net Income={_fmt(p['net_income'])}"
        )
    lines.append("")
    lines.append(f"{len(periods)} fiscal period(s) provided.")
    return "\n".join(lines)


INSIGHTS_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_business_insights",
        "description": "Return a structured, plain-language summary of a public company's business and recent financial performance, based strictly on the income statement data provided in the prompt.",
        "parameters": BusinessInsights.model_json_schema(),
    },
}


def _call_llm(ticker: str, periods: list[dict]) -> dict:
    if not groq_client:
        raise InsightsNotConfiguredError()

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(ticker, periods)},
            ],
            tools=[INSIGHTS_TOOL],
            tool_choice={"type": "function", "function": {"name": "generate_business_insights"}},
        )
    except groq.APIError as e:
        print(f"insights LLM call failed for {ticker}: {e}")
        raise LLMGenerationError() from e

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise LLMGenerationError()
    try:
        return json.loads(tool_calls[0].function.arguments)
    except json.JSONDecodeError as e:
        raise LLMGenerationError() from e


def _fetch_cached(ticker: str) -> dict | None:
    if not supabase:
        return None
    try:
        res = supabase.table("ai_insights").select("*").eq("ticker", ticker).maybe_single().execute()
        return res.data
    except Exception:
        return None


def _upsert_cache(record: dict):
    if not supabase:
        return
    supabase.table("ai_insights").upsert(record, on_conflict="ticker").execute()


def _is_stale(generated_at_iso: str) -> bool:
    generated_at = datetime.fromisoformat(generated_at_iso.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - generated_at > INSIGHTS_CACHE_TTL


def _build_record(ticker: str, periods: list[dict], summary: dict) -> dict:
    return {
        "ticker": ticker,
        "business_overview": summary["business_overview"],
        "income_statement_summary": summary["income_statement_summary"],
        "performance_verdict": summary["performance_verdict"],
        "performance_drivers": summary["performance_drivers"],
        "notable_flags": summary["notable_flags"],
        "data_basis": summary["data_basis"],
        "latest_fiscal_period_end": periods[0]["period_end"],
        "model": GROQ_MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _to_response(record: dict, cached: bool) -> dict:
    return {
        "ticker": record["ticker"],
        "business_overview": record["business_overview"],
        "income_statement_summary": record["income_statement_summary"],
        "performance_verdict": record["performance_verdict"],
        "performance_drivers": record["performance_drivers"],
        "notable_flags": record["notable_flags"],
        "data_basis": record["data_basis"],
        "generated_at": record["generated_at"],
        "cached": cached,
    }
