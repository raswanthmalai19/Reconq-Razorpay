"""Seeded synthetic data generator for ReconQ.

Produces settlement_report.csv, internal_ledger.csv and a held-out
ground_truth.csv. The matching engine never reads ground_truth.csv at
inference time -- it exists only so the evaluation harness can score
the pipeline honestly.
"""
import csv
import os
import random
import zlib
from datetime import date, timedelta

random.seed(42)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

N_TRUE_TRANSACTIONS = 150
BASE_DATE = date(2026, 8, 1)

# Target share of each injected mismatch class (must sum to 1.0)
CLASS_WEIGHTS = [
    ("exact_match", 0.65),
    ("fee_or_rounding", 0.10),
    ("timing_difference", 0.08),
    ("partial_refund", 0.05),
    ("split_or_merged", 0.04),
    ("duplicate", 0.03),
    ("genuinely_missing", 0.03),
    ("incorrect_reference", 0.02),
]

CUSTOMER_NAMES = ["Acme", "Globex", "Initech", "Umbrella", "Soylent", "Vandelay",
                   "Hooli", "Stark", "Wayne", "Wonka", "Cyberdyne", "Aperture"]


def money(rupees: float) -> int:
    """Convert rupees to integer paise."""
    return int(round(rupees * 100))


def gen_true_transaction(i: int):
    amount_rupees = random.choice([
        round(random.uniform(50, 999), 2),
        round(random.uniform(1000, 24999), 2),
        round(random.uniform(25000, 99999), 2),
        round(random.uniform(100000, 500000), 2),
    ])
    txn_date = BASE_DATE + timedelta(days=random.randint(0, 30))
    customer = random.choice(CUSTOMER_NAMES)
    invoice_id = f"INV-{2000 + i}"
    settlement_id = f"STL-{100000 + i}"
    utr = f"UTR2026{txn_date.strftime('%m%d')}{1000 + i:05d}"
    return {
        "i": i,
        "amount_paise": money(amount_rupees),
        "date": txn_date,
        "customer": customer,
        "invoice_id": invoice_id,
        "settlement_id": settlement_id,
        "utr": utr,
    }


def apply_mismatch(txn, cls):
    """Given a true transaction, produce (settlement_row, ledger_rows, ground_truth_rows)."""
    amt = txn["amount_paise"]
    d = txn["date"]
    settlement_narration = f"Settlement for {txn['invoice_id']} batch {d.strftime('%d%b')}"
    ledger_memo = f"Payment received - order {txn['i']}"

    settlement = {
        "settlement_id": txn["settlement_id"],
        "utr_reference": txn["utr"],
        "amount_inr": amt,
        "settlement_date": d.isoformat(),
        "fee_inr": 0,
        "tax_inr": 0,
        "narration": settlement_narration,
        "batch_id": f"BATCH-{txn['i'] // 10:04d}",
    }
    ledger = {
        "invoice_id": txn["invoice_id"],
        "customer_ref": f"CUST-{zlib.crc32(txn['customer'].encode()) % 9000 + 1000}",
        "amount_inr": amt,
        "invoice_date": d.isoformat(),
        "memo": ledger_memo,
        "status": "paid",
    }
    gt_rows = []
    ledgers = [ledger]

    if cls == "exact_match":
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})

    elif cls == "fee_or_rounding":
        fee = money(round(amt / 100 * random.uniform(1.5, 3.0) / 100, 2))
        settlement["amount_inr"] = amt - fee
        settlement["fee_inr"] = fee
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})

    elif cls == "timing_difference":
        settlement["settlement_date"] = (d + timedelta(days=random.randint(1, 3))).isoformat()
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})

    elif cls == "partial_refund":
        refund_pct = random.uniform(0.1, 0.4)
        settlement["amount_inr"] = int(amt * (1 - refund_pct))
        ledger["status"] = "partial"
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})

    elif cls == "split_or_merged":
        n_parts = random.choice([2, 3])
        shares = [random.random() for _ in range(n_parts)]
        total_share = sum(shares)
        ledgers = []
        for k in range(n_parts):
            part_amt = int(amt * shares[k] / total_share)
            if k == n_parts - 1:
                part_amt = amt - sum(l["amount_inr"] for l in ledgers)
            part_invoice = f"{txn['invoice_id']}-{k+1}"
            ledgers.append({
                "invoice_id": part_invoice,
                "customer_ref": ledger["customer_ref"],
                "amount_inr": part_amt,
                "invoice_date": d.isoformat(),
                "memo": f"Payment received - order {txn['i']} part {k+1}",
                "status": "paid",
            })
            gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": part_invoice,
                             "true_class": cls, "should_match": True, "match_type": "split"})
        settlement["narration"] = f"Settlement for {txn['invoice_id']} split batch {d.strftime('%d%b')}"

    elif cls == "duplicate":
        dup_settlement = dict(settlement)
        dup_settlement["settlement_id"] = f"{settlement['settlement_id']}-DUP"
        dup_settlement["utr_reference"] = f"{txn['utr']}D"
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})
        gt_rows.append({"settlement_id": dup_settlement["settlement_id"], "invoice_id": "",
                         "true_class": cls, "should_match": False, "match_type": "duplicate"})
        return [settlement, dup_settlement], ledgers, gt_rows

    elif cls == "genuinely_missing":
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": "",
                         "true_class": cls, "should_match": False, "match_type": "none"})
        return [settlement], [], gt_rows

    elif cls == "incorrect_reference":
        settlement["narration"] = f"Settlement misc batch {d.strftime('%d%b')} ref garbled"
        ledger["memo"] = "Payment received - order UNKNOWN"
        gt_rows.append({"settlement_id": settlement["settlement_id"], "invoice_id": ledger["invoice_id"],
                         "true_class": cls, "should_match": True, "match_type": "1:1"})

    return [settlement], ledgers, gt_rows


def assign_classes(n):
    classes = []
    for cls, share in CLASS_WEIGHTS:
        classes += [cls] * round(n * share)
    while len(classes) < n:
        classes.append("exact_match")
    classes = classes[:n]
    random.shuffle(classes)
    return classes


def generate():
    classes = assign_classes(N_TRUE_TRANSACTIONS)
    settlements, ledgers, ground_truth = [], [], []

    for i in range(N_TRUE_TRANSACTIONS):
        txn = gen_true_transaction(i)
        s_rows, l_rows, gt_rows = apply_mismatch(txn, classes[i])
        settlements.extend(s_rows)
        ledgers.extend(l_rows)
        ground_truth.extend(gt_rows)

    random.shuffle(settlements)
    random.shuffle(ledgers)

    write_csv(os.path.join(OUT_DIR, "settlement_report.csv"), settlements,
              ["settlement_id", "utr_reference", "amount_inr", "settlement_date",
               "fee_inr", "tax_inr", "narration", "batch_id"])
    write_csv(os.path.join(OUT_DIR, "internal_ledger.csv"), ledgers,
              ["invoice_id", "customer_ref", "amount_inr", "invoice_date", "memo", "status"])
    write_csv(os.path.join(OUT_DIR, "ground_truth.csv"), ground_truth,
              ["settlement_id", "invoice_id", "true_class", "should_match", "match_type"])

    print(f"Generated {len(settlements)} settlement rows, {len(ledgers)} ledger rows, "
          f"{len(ground_truth)} ground-truth rows from {N_TRUE_TRANSACTIONS} true transactions.")
    class_counts = {}
    for c in classes:
        class_counts[c] = class_counts.get(c, 0) + 1
    for cls, share in CLASS_WEIGHTS:
        print(f"  {cls}: {class_counts.get(cls, 0)} ({class_counts.get(cls, 0)/N_TRUE_TRANSACTIONS:.1%})")


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    generate()
