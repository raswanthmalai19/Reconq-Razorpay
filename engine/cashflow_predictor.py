"""Predictive Cash Flow Intelligence Engine.

Analyzes historical settlement patterns to:
1. Predict expected incoming settlements for the next 7 days
2. Identify delayed settlements (expected but not yet received)
3. Calculate cash flow velocity and variance
4. Generate daily/weekly forecasts with confidence intervals
5. Detect seasonal patterns and anomalous cash flow days

This is the feature that transforms ReconQ from backward-looking
(what happened?) to forward-looking (what's going to happen?).
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import os


def analyze_cashflow(
    settlement_path: str,
    ledger_path: str,
    bank_path: Optional[str] = None,
    reconciliation_result: Optional[dict] = None,
) -> dict:
    """Run full cash flow predictive analysis.

    Returns a rich dict with predictions, alerts, and insights.
    """
    settlements = pd.read_csv(settlement_path)
    ledger = pd.read_csv(ledger_path)

    settlements["settlement_date"] = pd.to_datetime(settlements["settlement_date"])
    settlements["amount_rupees"] = settlements["amount_inr"] / 100
    settlements["fee_rupees"] = settlements["fee_inr"] / 100
    settlements["net_rupees"] = settlements["amount_rupees"] - settlements["fee_rupees"]

    ledger["invoice_date"] = pd.to_datetime(ledger["invoice_date"])
    ledger["amount_rupees"] = ledger["amount_inr"] / 100

    today = settlements["settlement_date"].max() + timedelta(days=1)

    # ── 1. Daily Settlement Pattern Analysis ─────────────────────────
    daily = (
        settlements.groupby(settlements["settlement_date"].dt.date)
        .agg(
            count=("settlement_id", "count"),
            total_rupees=("amount_rupees", "sum"),
            net_rupees=("net_rupees", "sum"),
            avg_amount=("amount_rupees", "mean"),
            max_amount=("amount_rupees", "max"),
            total_fees=("fee_rupees", "sum"),
        )
        .reset_index()
    )
    daily.columns = ["date", "count", "total_rupees", "net_rupees", "avg_amount", "max_amount", "total_fees"]
    daily["date"] = pd.to_datetime(daily["date"])

    # ── 2. Day-of-Week Pattern (for prediction) ─────────────────────
    daily["dow"] = daily["date"].dt.dayofweek
    dow_pattern = (
        daily.groupby("dow")
        .agg(
            avg_count=("count", "mean"),
            avg_total=("total_rupees", "mean"),
            std_total=("total_rupees", "std"),
            avg_net=("net_rupees", "mean"),
        )
        .reset_index()
    )
    dow_pattern["std_total"] = dow_pattern["std_total"].fillna(0)
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_pattern["day_name"] = dow_pattern["dow"].map(lambda x: dow_names[x])

    # ── 3. 7-Day Cash Flow Forecast ──────────────────────────────────
    forecast = []
    for i in range(1, 8):
        pred_date = today + timedelta(days=i - 1)
        dow = pred_date.weekday()
        row = dow_pattern[dow_pattern["dow"] == dow]
        if len(row) > 0:
            avg = float(row["avg_total"].iloc[0])
            std = float(row["std_total"].iloc[0])
            avg_count = float(row["avg_count"].iloc[0])
            avg_net = float(row["avg_net"].iloc[0])
        else:
            avg = float(daily["total_rupees"].mean())
            std = float(daily["total_rupees"].std())
            avg_count = float(daily["count"].mean())
            avg_net = float(daily["net_rupees"].mean())

        forecast.append({
            "date": pred_date.strftime("%Y-%m-%d"),
            "day_name": dow_names[dow],
            "predicted_amount_rupees": round(avg, 2),
            "predicted_net_rupees": round(avg_net, 2),
            "confidence_low": round(max(0, avg - 1.5 * std), 2),
            "confidence_high": round(avg + 1.5 * std, 2),
            "predicted_count": round(avg_count),
            "confidence_pct": round(min(95, 70 + (10 / (1 + std / max(avg, 1))) * 3), 1),
        })

    total_forecast_7d = sum(f["predicted_amount_rupees"] for f in forecast)
    total_forecast_net_7d = sum(f["predicted_net_rupees"] for f in forecast)

    # ── 4. Settlement Delay Detection ────────────────────────────────
    # Identify invoices that were expected to settle but haven't
    pending_invoices = ledger[ledger["status"] == "partial"]
    delayed_settlements = []

    for _, inv in pending_invoices.iterrows():
        expected_date = inv["invoice_date"] + timedelta(days=2)  # T+2 settlement
        days_overdue = (today - expected_date).days
        if days_overdue > 0:
            delayed_settlements.append({
                "invoice_id": inv["invoice_id"],
                "amount_rupees": round(float(inv["amount_rupees"]), 2),
                "invoice_date": inv["invoice_date"].strftime("%Y-%m-%d"),
                "expected_settlement": expected_date.strftime("%Y-%m-%d"),
                "days_overdue": int(days_overdue),
                "risk_level": "CRITICAL" if days_overdue > 5 else "HIGH" if days_overdue > 3 else "MEDIUM",
            })

    delayed_settlements.sort(key=lambda x: x["days_overdue"], reverse=True)
    total_delayed_rupees = sum(d["amount_rupees"] for d in delayed_settlements)

    # ── 5. Cash Flow Velocity Metrics ────────────────────────────────
    total_settled = float(settlements["amount_rupees"].sum())
    total_net = float(settlements["net_rupees"].sum())
    total_fees = float(settlements["fee_rupees"].sum())
    date_range_days = (settlements["settlement_date"].max() - settlements["settlement_date"].min()).days + 1

    avg_daily_inflow = total_settled / max(date_range_days, 1)
    avg_daily_net = total_net / max(date_range_days, 1)
    fee_rate_pct = (total_fees / total_settled * 100) if total_settled > 0 else 0

    # Settlement speed: avg days between invoice date and settlement date
    merged = settlements.merge(
        ledger,
        left_on=settlements["amount_inr"],
        right_on=ledger["amount_inr"],
        how="inner",
        suffixes=("_s", "_l"),
    )
    if len(merged) > 0 and "invoice_date" in merged.columns and "settlement_date" in merged.columns:
        merged["settlement_days"] = (merged["settlement_date"] - merged["invoice_date"]).dt.days
        avg_settlement_days = float(merged["settlement_days"].mean())
    else:
        avg_settlement_days = 2.0

    # Daily variance (volatility)
    daily_volatility_pct = (float(daily["total_rupees"].std()) / avg_daily_inflow * 100) if avg_daily_inflow > 0 else 0

    # ── 6. Amount Band Forecast ──────────────────────────────────────
    bands = [
        (0, 1000, "₹0-1K (Micro)"),
        (1000, 25000, "₹1K-25K (Small)"),
        (25000, 100000, "₹25K-1L (Medium)"),
        (100000, float("inf"), "₹1L+ (Large)"),
    ]
    band_analysis = []
    for lo, hi, label in bands:
        band_df = settlements[(settlements["amount_rupees"] >= lo) & (settlements["amount_rupees"] < hi)]
        if len(band_df) > 0:
            band_analysis.append({
                "band": label,
                "count": int(len(band_df)),
                "total_rupees": round(float(band_df["amount_rupees"].sum()), 2),
                "avg_rupees": round(float(band_df["amount_rupees"].mean()), 2),
                "pct_of_total": round(len(band_df) / len(settlements) * 100, 1),
                "pct_of_value": round(float(band_df["amount_rupees"].sum()) / total_settled * 100, 1),
            })

    # ── 7. Weekly Trend (for the chart) ──────────────────────────────
    daily_chart = []
    for _, row in daily.iterrows():
        daily_chart.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "total_rupees": round(float(row["total_rupees"]), 2),
            "net_rupees": round(float(row["net_rupees"]), 2),
            "count": int(row["count"]),
        })

    # ── 8. Peak / Trough Days ────────────────────────────────────────
    peak_day = daily.loc[daily["total_rupees"].idxmax()]
    trough_day = daily.loc[daily["total_rupees"].idxmin()]

    # ── Assemble Final Result ────────────────────────────────────────
    return {
        "generated_at": datetime.now().isoformat(),
        "analysis_period": {
            "start": settlements["settlement_date"].min().strftime("%Y-%m-%d"),
            "end": settlements["settlement_date"].max().strftime("%Y-%m-%d"),
            "days": int(date_range_days),
        },
        "velocity": {
            "total_settled_rupees": round(total_settled, 2),
            "total_net_rupees": round(total_net, 2),
            "total_fees_rupees": round(total_fees, 2),
            "avg_daily_inflow_rupees": round(avg_daily_inflow, 2),
            "avg_daily_net_rupees": round(avg_daily_net, 2),
            "avg_settlement_days": round(avg_settlement_days, 1),
            "fee_rate_pct": round(fee_rate_pct, 2),
            "daily_volatility_pct": round(daily_volatility_pct, 1),
            "total_transactions": int(len(settlements)),
        },
        "forecast_7d": {
            "total_predicted_rupees": round(total_forecast_7d, 2),
            "total_predicted_net_rupees": round(total_forecast_net_7d, 2),
            "daily": forecast,
        },
        "delayed_settlements": {
            "count": len(delayed_settlements),
            "total_rupees": round(total_delayed_rupees, 2),
            "items": delayed_settlements[:20],
        },
        "daily_chart": daily_chart,
        "band_analysis": band_analysis,
        "dow_pattern": [
            {
                "day": dow_names[int(row["dow"])],
                "avg_rupees": round(float(row["avg_total"]), 2),
                "avg_count": round(float(row["avg_count"]), 1),
            }
            for _, row in dow_pattern.iterrows()
        ],
        "highlights": {
            "peak_day": {
                "date": peak_day["date"].strftime("%Y-%m-%d"),
                "amount_rupees": round(float(peak_day["total_rupees"]), 2),
            },
            "trough_day": {
                "date": trough_day["date"].strftime("%Y-%m-%d"),
                "amount_rupees": round(float(trough_day["total_rupees"]), 2),
            },
        },
    }
