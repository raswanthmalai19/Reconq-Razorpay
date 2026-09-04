import requests
import time
import json
import os

BASE_URL = "http://localhost:8000/api"

def print_step(msg):
    print(f"\n\033[94m==> {msg}\033[0m")

def test_api():
    # 1. Razorpay Status
    print_step("Testing Razorpay Status")
    res = requests.get(f"{BASE_URL}/razorpay/status")
    print(res.json())
    assert res.json().get("configured") is True, "Keys not configured"

    # 2. Razorpay Sync
    print_step("Testing Razorpay Sync (API Mode)")
    res = requests.post(f"{BASE_URL}/razorpay/sync")
    data = res.json()
    assert "error" not in data, data.get("error")
    run_id_api = data.get("run_id")
    if data.get("status") == "no_settlements":
        # Honest empty state: this test Razorpay account has no real settlements yet.
        print(f"No live settlements (expected for a fresh test account): {data.get('razorpay_message')}")
        assert run_id_api is None
    else:
        print(f"Run ID: {run_id_api}")
        print(f"KPI: {data.get('kpi', {}).get('total_records')} records")
        assert run_id_api is not None, "Razorpay Sync failed"

    # 3. Sample CSV Reconcile
    print_step("Testing CSV Upload Mode (Sample Data)")
    res = requests.post(f"{BASE_URL}/reconcile/sample")
    data = res.json()
    run_id_csv = data.get("run_id")
    print(f"Run ID: {run_id_csv}")
    print(f"KPI: {data.get('kpi', {}).get('total_records')} records")
    assert run_id_csv is not None, "CSV Reconcile failed"

    # 4. Audit Log (Checking timestamp fix)
    print_step("Testing Audit Log")
    audit_run_id = run_id_api or run_id_csv
    res = requests.get(f"{BASE_URL}/audit/{audit_run_id}")
    logs = res.json()
    print(f"Fetched {len(logs)} logs.")
    if logs:
        ts = logs[0].get("timestamp")
        print(f"Latest timestamp format: {ts}")
        assert "T" in ts and "Z" not in ts or "Z" in ts or "+" in ts, "Timestamp doesn't look like ISO"

    # 5. Suggested Fix (LLM test)
    print_step("Testing Suggested Fix Generation")
    payload = {
        "settlement_id": "setl_12345",
        "amount_paise": 50000,
        "confidence": 0.82,
        "status": "HUMAN_REVIEW",
        "match_type": "partial_amount"
    }
    t0 = time.time()
    res = requests.post(f"{BASE_URL}/suggested-fix/generate", json=payload)
    t1 = time.time()
    data = res.json()
    print(f"Took {t1-t0:.2f}s")
    print(f"Adjustment Type: {data.get('adjustment_type')}")
    assert "adjustment_type" in data, "Suggested fix format invalid"

    # 6. Copilot Chat
    print_step("Testing Copilot Chat")
    payload = {
        "message": "What is my match rate?",
        "run_id": run_id_csv
    }
    t0 = time.time()
    res = requests.post(f"{BASE_URL}/copilot/chat", json=payload)
    t1 = time.time()
    data = res.json()
    print(f"Took {t1-t0:.2f}s")
    print(f"Reply snippet: {data.get('reply', '')[:100]}...")
    assert "reply" in data, "Copilot chat failed"
    
    print_step("ALL TESTS PASSED SUCCESSFULLY! 🚀")

if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"\n\033[91mERROR: {e}\033[0m")
