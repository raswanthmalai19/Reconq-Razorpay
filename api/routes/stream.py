from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from datetime import datetime
from engine.simulator import generate_batch

router = APIRouter()

@router.websocket('/ws/stream')
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    
    stats = {
        "total_processed": 0,
        "auto_matched": 0,
        "review_queue": 0,
        "anomalies_found": 0,
        "total_amount_rupees": 0.0,
        "leakage_detected_rupees": 0.0
    }
    
    try:
        while True:
            # Generate a batch every 1.5 seconds
            await asyncio.sleep(1.5)
            settlements, ledgers = generate_batch(batch_size=random_batch_size())
            
            # Map ledgers for easy lookup if there were shuffling, though here they correspond mostly
            # We'll just zip them, but simulator gives them in order. 
            # Note: 2% duplicate anomaly added duplicate settlement, so lengths might mismatch.
            # Let's handle matching logic simply:
            ledger_map = {l['invoice_id']: l for l in ledgers}
            
            for stl in settlements:
                stats["total_processed"] += 1
                stats["total_amount_rupees"] += stl["amount_inr"] / 100.0
                
                # Extract counter from STL-LIVE-XXX to find corresponding INV-LIVE-XXX
                counter = stl["settlement_id"].split("-")[-1]
                inv_id = f"INV-LIVE-{counter}"
                
                ldr = ledger_map.get(inv_id)
                
                match_result = "AUTO_MATCHED"
                anomaly_type = None
                confidence = 0.99
                
                if not ldr:
                    match_result = "ANOMALY"
                    anomaly_type = "Orphan Settlement"
                    confidence = 0.20
                    stats["anomalies_found"] += 1
                else:
                    # Check amount
                    if stl["amount_inr"] != ldr["amount_inr"]:
                        match_result = "ANOMALY"
                        anomaly_type = "Amount Mismatch"
                        confidence = 0.40
                        stats["anomalies_found"] += 1
                        stats["leakage_detected_rupees"] += abs(stl["amount_inr"] - ldr["amount_inr"]) / 100.0
                    
                    # Check timing
                    stl_date = datetime.fromisoformat(stl["settlement_date"])
                    ldr_date = datetime.fromisoformat(ldr["invoice_date"])
                    if (stl_date - ldr_date).days >= 3:
                        if match_result == "AUTO_MATCHED":
                            match_result = "HUMAN_REVIEW"
                            anomaly_type = "Timing Delay"
                            confidence = 0.65
                            stats["review_queue"] += 1
                    
                    # Check fee
                    expected_fee = int(stl["amount_inr"] * 0.02)
                    if stl["fee_inr"] > expected_fee * 1.1: # Allow some tolerance
                        if match_result == "AUTO_MATCHED":
                            match_result = "ANOMALY"
                            anomaly_type = "Fee Overcharge"
                            confidence = 0.30
                            stats["anomalies_found"] += 1
                            stats["leakage_detected_rupees"] += (stl["fee_inr"] - expected_fee) / 100.0
                
                if match_result == "AUTO_MATCHED":
                    stats["auto_matched"] += 1

                # Send transaction
                await websocket.send_json({
                    "type": "transaction",
                    "data": {
                        "settlement": stl,
                        "ledger": ldr,
                        "match_result": match_result,
                        "confidence": confidence,
                        "anomaly_type": anomaly_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                
            # Send stats
            await websocket.send_json({
                "type": "stats",
                "data": {
                    "total_processed": stats["total_processed"],
                    "auto_matched": stats["auto_matched"],
                    "review_queue": stats["review_queue"],
                    "anomalies_found": stats["anomalies_found"],
                    "total_amount_rupees": round(stats["total_amount_rupees"], 2),
                    "leakage_detected_rupees": round(stats["leakage_detected_rupees"], 2)
                }
            })
            
    except WebSocketDisconnect:
        pass

import random
def random_batch_size():
    return random.randint(3, 5)
