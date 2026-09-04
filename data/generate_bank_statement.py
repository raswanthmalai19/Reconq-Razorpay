import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_bank_statement():
    settlement_path = os.path.join(OUT_DIR, "settlement_report.csv")
    if not os.path.exists(settlement_path):
        print(f"Error: {settlement_path} not found. Run generate_data.py first.")
        return
        
    settlements = []
    with open(settlement_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            settlements.append(row)
            
    bank_statements = []
    ground_truths = []
    
    for i, s in enumerate(settlements):
        s_id = s["settlement_id"]
        utr = s["utr_reference"]
        amt = int(s["amount_inr"])
        date_str = s["settlement_date"]
        
        try:
            dt = datetime.fromisoformat(date_str)
        except ValueError:
            # fallback if it's just a date
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        rand_val = random.random()
        
        if rand_val < 0.80:
            cls = "perfect_match"
            credit_amount = amt
            credit_date = dt
            should_match = True
        elif rand_val < 0.88:
            cls = "timing_delay"
            credit_amount = amt
            credit_date = dt + timedelta(days=random.randint(2, 5))
            should_match = True
        elif rand_val < 0.93:
            cls = "bank_charge"
            charge = random.randint(500, 5000)
            credit_amount = max(0, amt - charge)
            credit_date = dt
            should_match = True
        elif rand_val < 0.97:
            cls = "missing_from_bank"
            ground_truths.append({
                "settlement_id": s_id,
                "bank_txn_id": "",
                "true_class": cls,
                "should_match": False
            })
            continue
        else:
            cls = "amount_mismatch"
            diff = random.randint(-5000, 5000)
            if diff == 0: diff = 1000
            credit_amount = max(0, amt + diff)
            credit_date = dt
            should_match = False
            
        bank_txn_id = f"BNK-{50001 + i}"
        
        bank_statements.append({
            "bank_txn_id": bank_txn_id,
            "utr_reference": utr,
            "credit_amount_inr": credit_amount,
            "credit_date": credit_date.isoformat(),
            "bank_narration": f"NEFT from Razorpay {utr}",
            "balance_after": 0  # To be calculated
        })
        
        ground_truths.append({
            "settlement_id": s_id,
            "bank_txn_id": bank_txn_id,
            "true_class": cls,
            "should_match": should_match
        })
        
    bank_statements.sort(key=lambda x: x["credit_date"])
    
    current_balance = 10000000
    for bs in bank_statements:
        current_balance += bs["credit_amount_inr"]
        bs["balance_after"] = current_balance

    with open(os.path.join(OUT_DIR, "bank_statement.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["bank_txn_id", "utr_reference", "credit_amount_inr", "credit_date", "bank_narration", "balance_after"])
        writer.writeheader()
        writer.writerows(bank_statements)
        
    with open(os.path.join(OUT_DIR, "bank_ground_truth.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["settlement_id", "bank_txn_id", "true_class", "should_match"])
        writer.writeheader()
        writer.writerows(ground_truths)
        
    print(f"Generated {len(bank_statements)} bank statements and {len(ground_truths)} ground truth rows.")

if __name__ == "__main__":
    generate_bank_statement()
