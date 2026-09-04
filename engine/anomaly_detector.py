import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Anomaly:
    type_name: str
    severity: str
    estimated_impact_paise: int
    description: str
    affected_records: List[str]
    
    def to_dict(self):
        return {
            "type_name": self.type_name,
            "severity": self.severity,
            "estimated_impact_paise": self.estimated_impact_paise,
            "description": self.description,
            "affected_records": self.affected_records
        }

@dataclass
class LeakageReport:
    total_leakage_paise: int
    by_category: Dict[str, int]
    recommendations: List[str]
    
    def to_dict(self):
        return {
            "total_leakage_paise": self.total_leakage_paise,
            "by_category": self.by_category,
            "recommendations": self.recommendations
        }

def detect_anomalies(settlements_df: pd.DataFrame, ledgers_df: pd.DataFrame, 
                     reconciliation_result: Dict[str, Any], bank_result: Optional[Dict[str, Any]] = None) -> List[Anomaly]:
    anomalies = []

    # 1. Fee Overcharges
    expected_mdr = 0.02
    fee_overcharges = []
    total_overcharge_impact = 0
    for _, row in settlements_df.iterrows():
        amt = row['amount_inr']
        fee = row.get('fee_inr', 0)
        if pd.notna(fee) and pd.notna(amt) and fee > 0:
            expected_fee = amt * expected_mdr
            if fee > expected_fee * 1.5:
                fee_overcharges.append(row['settlement_id'])
                total_overcharge_impact += int(fee - expected_fee)
    
    if fee_overcharges:
        anomalies.append(Anomaly(
            type_name="Fee Overcharge",
            severity="MEDIUM" if len(fee_overcharges) < 10 else "HIGH",
            estimated_impact_paise=total_overcharge_impact,
            description=f"Found {len(fee_overcharges)} settlements with fees > 1.5x expected MDR (2%).",
            affected_records=fee_overcharges
        ))

    # 2. Timing Delays
    if bank_result and 'bank_discrepancies' in bank_result:
        delays = []
        delay_impact = 0
        for disc in bank_result['bank_discrepancies']:
            if disc['date_delta'] > 3:
                delays.append(disc['settlement_id'])
                delay_impact += disc['amount_inr']
        
        if delays:
            anomalies.append(Anomaly(
                type_name="Timing Delay",
                severity="MEDIUM",
                estimated_impact_paise=delay_impact,
                description=f"Found {len(delays)} settlements with > 3 days delay in bank credit.",
                affected_records=delays
            ))

    # 3. Duplicate Patterns
    if 'settlement_date' in settlements_df.columns:
        dates_to_use = settlements_df['settlement_date']
        if not pd.api.types.is_datetime64_any_dtype(dates_to_use):
             dates_to_use = pd.to_datetime(dates_to_use)
        
        temp_df = settlements_df.copy()
        temp_df['date_only'] = dates_to_use.dt.date
        
        dups = temp_df.duplicated(subset=['amount_inr', 'date_only'], keep=False)
        dup_rows = temp_df[dups]
        
        if len(dup_rows) > 0:
            affected = dup_rows['settlement_id'].tolist()
            impact = int(dup_rows['amount_inr'].sum()) // 2
            anomalies.append(Anomaly(
                type_name="Duplicate Pattern",
                severity="HIGH",
                estimated_impact_paise=impact,
                description=f"Found {len(affected)} potentially duplicate settlements (same amount and date).",
                affected_records=affected
            ))

    # 4. Missing Settlement Patterns
    unresolved_ledgers = reconciliation_result.get('unresolved_ledgers', [])
    if unresolved_ledgers:
        missing_df = ledgers_df[ledgers_df['invoice_id'].isin(unresolved_ledgers)]
        impact = int(missing_df['amount_inr'].sum())
        anomalies.append(Anomaly(
            type_name="Missing Settlement",
            severity="CRITICAL",
            estimated_impact_paise=impact,
            description=f"Found {len(unresolved_ledgers)} ledger entries with no corresponding settlement.",
            affected_records=unresolved_ledgers
        ))

    return anomalies

def generate_leakage_report(anomalies: List[Anomaly]) -> LeakageReport:
    total = sum(a.estimated_impact_paise for a in anomalies)
    by_cat = {}
    for a in anomalies:
        by_cat[a.type_name] = by_cat.get(a.type_name, 0) + a.estimated_impact_paise
    
    recs = []
    if "Missing Settlement" in by_cat:
        recs.append("Investigate missing settlements immediately to prevent revenue leakage.")
    if "Duplicate Pattern" in by_cat:
        recs.append("Review duplicate settlement entries to ensure no double-counting.")
    if "Fee Overcharge" in by_cat:
        recs.append("Review MDR agreements with payment gateway.")
    if "Timing Delay" in by_cat:
        recs.append("Follow up with bank regarding delayed credits.")
    if not recs:
        recs.append("No critical issues found. Maintain regular monitoring.")
    
    return LeakageReport(
        total_leakage_paise=total,
        by_category=by_cat,
        recommendations=recs
    )
