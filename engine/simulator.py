import random
import uuid
import datetime

class TransactionSimulator:
    def __init__(self):
        self.counter = 1000

    def generate_batch(self, batch_size=5):
        settlements = []
        ledgers = []

        for _ in range(batch_size):
            self.counter += 1
            
            # Base data
            amount_inr = random.randint(1000, 100000) * 100 # paise
            fee_inr = int(amount_inr * 0.02)
            tax_inr = int(fee_inr * 0.18)
            
            # Dates
            base_date = datetime.date.today() - datetime.timedelta(days=random.randint(0, 30))
            settlement_date = base_date
            invoice_date = base_date
            
            settlement_id = f"STL-LIVE-{self.counter}"
            invoice_id = f"INV-LIVE-{self.counter}"
            utr = f"UTR-SYN-{self.counter}"
            batch_id = f"BATCH-LIVE-{self.counter}"
            cust_ref = f"CUST-{self.counter}"
            
            # Determine anomalies
            r = random.random()
            
            ledger_amount = amount_inr
            settlement_amount = amount_inr
            actual_fee = fee_inr
            
            is_duplicate = False
            
            if r < 0.02: # 2% duplicate
                is_duplicate = True
            elif r < 0.05: # 3% amount mismatch (cumulative 0.02 to 0.05)
                ledger_amount = amount_inr + random.choice([-1000, 1000, -500, 500])
            elif r < 0.10: # 5% timing delay (cumulative 0.05 to 0.10)
                settlement_date = base_date + datetime.timedelta(days=random.randint(3, 7))
            elif r < 0.20: # 10% fee overcharge (cumulative 0.10 to 0.20)
                actual_fee = fee_inr * 2
            
            settlement = {
                "settlement_id": settlement_id,
                "utr_reference": utr,
                "amount_inr": settlement_amount,
                "settlement_date": settlement_date.isoformat(),
                "fee_inr": actual_fee,
                "tax_inr": tax_inr,
                "narration": f"Settlement for {invoice_id} batch {batch_id}",
                "batch_id": batch_id
            }
            
            ledger = {
                "invoice_id": invoice_id,
                "customer_ref": cust_ref,
                "amount_inr": ledger_amount,
                "invoice_date": invoice_date.isoformat(),
                "memo": f"Auto-paid {invoice_id}",
                "status": "paid"
            }
            
            settlements.append(settlement)
            ledgers.append(ledger)
            
            if is_duplicate:
                # Add duplicate to settlements
                settlements.append(settlement.copy())

        return settlements, ledgers

# Singleton instance
simulator = TransactionSimulator()

def generate_batch(batch_size=5):
    return simulator.generate_batch(batch_size)
