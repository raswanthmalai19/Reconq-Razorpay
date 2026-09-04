import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class BankMatchResult:
    bank_confirmed: List[Dict[str, Any]]
    bank_discrepancies: List[Dict[str, Any]]
    funds_in_transit: List[Dict[str, Any]]
    bank_extras: List[Dict[str, Any]]
    
    def to_dict(self):
        return {
            "bank_confirmed": self.bank_confirmed,
            "bank_discrepancies": self.bank_discrepancies,
            "funds_in_transit": self.funds_in_transit,
            "bank_extras": self.bank_extras
        }

def load_bank_statement_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_columns = ["bank_txn_id", "utr_reference", "credit_amount_inr", "credit_date", "bank_narration", "balance_after"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    df['credit_date'] = pd.to_datetime(df['credit_date'])
    return df

def match_bank_to_settlements(bank_df: pd.DataFrame, settlements_df: pd.DataFrame) -> BankMatchResult:
    if not pd.api.types.is_datetime64_any_dtype(settlements_df['settlement_date']):
        settlements_df['settlement_date'] = pd.to_datetime(settlements_df['settlement_date'])
    if not pd.api.types.is_datetime64_any_dtype(bank_df['credit_date']):
        bank_df['credit_date'] = pd.to_datetime(bank_df['credit_date'])

    bank_confirmed = []
    bank_discrepancies = []
    funds_in_transit = []
    bank_extras = []

    merged = pd.merge(settlements_df, bank_df, on='utr_reference', how='outer', indicator=True)
    
    for _, row in merged.iterrows():
        if row['_merge'] == 'left_only':
            funds_in_transit.append({
                "settlement_id": row["settlement_id"],
                "utr_reference": row["utr_reference"],
                "amount_inr": row["amount_inr"],
                "settlement_date": row["settlement_date"].isoformat() if pd.notnull(row["settlement_date"]) else None,
                "status": "FUNDS_IN_TRANSIT"
            })
        elif row['_merge'] == 'right_only':
            bank_extras.append({
                "bank_txn_id": row["bank_txn_id"],
                "utr_reference": row["utr_reference"],
                "credit_amount_inr": row["credit_amount_inr"],
                "credit_date": row["credit_date"].isoformat() if pd.notnull(row["credit_date"]) else None,
                "bank_narration": row["bank_narration"],
                "status": "BANK_EXTRA"
            })
        elif row['_merge'] == 'both':
            amount_delta = abs(row["amount_inr"] - row["credit_amount_inr"])
            date_delta = abs((row["settlement_date"] - row["credit_date"]).days)
            
            match_dict = {
                "settlement_id": row["settlement_id"],
                "bank_txn_id": row["bank_txn_id"],
                "utr_reference": row["utr_reference"],
                "amount_inr": row["amount_inr"],
                "credit_amount_inr": row["credit_amount_inr"],
                "amount_delta": amount_delta,
                "settlement_date": row["settlement_date"].isoformat(),
                "credit_date": row["credit_date"].isoformat(),
                "date_delta": date_delta
            }
            
            if amount_delta <= 200 and date_delta <= 1:
                match_dict["status"] = "BANK_CONFIRMED"
                bank_confirmed.append(match_dict)
            else:
                match_dict["status"] = "BANK_DISCREPANCY"
                bank_discrepancies.append(match_dict)

    return BankMatchResult(
        bank_confirmed=bank_confirmed,
        bank_discrepancies=bank_discrepancies,
        funds_in_transit=funds_in_transit,
        bank_extras=bank_extras
    )
