"""Cash Flow Prediction API — predictive intelligence for settlement forecasting."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/cashflow/predict")
def predict_cashflow():
    """Generate full cash flow prediction from settlement data."""
    import os
    from engine.cashflow_predictor import analyze_cashflow

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    settlement_path = os.path.join(base, "data", "settlement_report.csv")
    ledger_path = os.path.join(base, "data", "internal_ledger.csv")

    result = analyze_cashflow(settlement_path, ledger_path)
    return result


@router.get("/cashflow/insights")
def cashflow_insights():
    """Generate AI-powered narrative insights for cash flow."""
    import os
    import json
    import re
    from engine.cashflow_predictor import analyze_cashflow

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    settlement_path = os.path.join(base, "data", "settlement_report.csv")
    ledger_path = os.path.join(base, "data", "internal_ledger.csv")

    cf = analyze_cashflow(settlement_path, ledger_path)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _template_insights(cf)

    try:
        from google import genai
        from google.genai import types

        model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a senior financial analyst. Generate exactly 5 actionable cash flow insights from this data.

DATA:
- Period: {cf['analysis_period']['days']} days
- Total settled: ₹{cf['velocity']['total_settled_rupees']:,.2f}
- Avg daily inflow: ₹{cf['velocity']['avg_daily_inflow_rupees']:,.2f}
- Fee rate: {cf['velocity']['fee_rate_pct']}%
- Volatility: {cf['velocity']['daily_volatility_pct']}%
- Avg settlement speed: {cf['velocity']['avg_settlement_days']} days
- 7-day forecast: ₹{cf['forecast_7d']['total_predicted_rupees']:,.2f}
- Delayed settlements: {cf['delayed_settlements']['count']} (₹{cf['delayed_settlements']['total_rupees']:,.2f})
- Peak day: {cf['highlights']['peak_day']['date']} (₹{cf['highlights']['peak_day']['amount_rupees']:,.2f})
- Trough day: {cf['highlights']['trough_day']['date']} (₹{cf['highlights']['trough_day']['amount_rupees']:,.2f})

Return a JSON array of 5 objects, each with:
{{"title": "short title", "insight": "2-3 sentence actionable insight", "impact": "HIGH" | "MEDIUM" | "LOW", "category": "FORECAST" | "RISK" | "OPTIMIZATION" | "TREND"}}

Return ONLY valid JSON. No markdown fences."""

        chat = client.chats.create(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction="You are a JSON API. Return only valid JSON arrays.",
                max_output_tokens=4096,
                temperature=0.2,
            ),
        )
        resp = chat.send_message(prompt)
        raw = resp.text or ""
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        insights = json.loads(raw)
        return {"source": "gemini", "insights": insights}

    except Exception:
        return _template_insights(cf)


def _template_insights(cf: dict) -> dict:
    v = cf["velocity"]
    f = cf["forecast_7d"]
    d = cf["delayed_settlements"]

    insights = [
        {
            "title": "7-Day Inflow Forecast",
            "insight": f"Based on day-of-week settlement patterns, expect approximately ₹{f['total_predicted_rupees']:,.0f} in gross inflows over the next 7 days (₹{f['total_predicted_net_rupees']:,.0f} net after fees). Plan working capital accordingly.",
            "impact": "HIGH",
            "category": "FORECAST",
        },
        {
            "title": "Settlement Velocity",
            "insight": f"Average settlement speed is {v['avg_settlement_days']} days from invoice to bank credit. Daily inflow averages ₹{v['avg_daily_inflow_rupees']:,.0f} across {v['total_transactions']} transactions.",
            "impact": "MEDIUM",
            "category": "TREND",
        },
        {
            "title": f"Fee Optimization Opportunity",
            "insight": f"Current effective fee rate is {v['fee_rate_pct']}%. Total fees paid: ₹{v['total_fees_rupees']:,.0f}. Negotiating a 0.2% reduction would save approximately ₹{v['total_settled_rupees'] * 0.002:,.0f} over the same period.",
            "impact": "HIGH",
            "category": "OPTIMIZATION",
        },
    ]

    if d["count"] > 0:
        insights.append({
            "title": f"{d['count']} Delayed Settlements",
            "insight": f"₹{d['total_rupees']:,.0f} in settlements are overdue beyond T+2 standard. Escalate with the acquiring bank immediately to prevent cash flow disruption.",
            "impact": "HIGH",
            "category": "RISK",
        })

    if v["daily_volatility_pct"] > 50:
        insights.append({
            "title": "High Cash Flow Volatility",
            "insight": f"Daily settlement variance is {v['daily_volatility_pct']:.0f}%. This indicates unpredictable cash flows — consider maintaining a higher working capital buffer.",
            "impact": "MEDIUM",
            "category": "RISK",
        })
    else:
        insights.append({
            "title": "Stable Cash Flow Pattern",
            "insight": f"Daily settlement variance is {v['daily_volatility_pct']:.0f}%, indicating predictable cash flows. This stability enables confident financial planning.",
            "impact": "LOW",
            "category": "TREND",
        })

    return {"source": "template", "insights": insights}
