"""ReconQ Streamlit dashboard: upload/sample data, staged processing, KPIs,
exception drill-down with Accept/Override, audit log, CSV export.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from engine.audit_log import append_event, append_override, get_all_events, init_db
from engine.confidence_model import load_model
from engine.ingestion import SchemaValidationError
from engine.pipeline import run_reconciliation
from engine.train import train_and_save
from llm.client import explain

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RUN_ID = "dashboard-session"

st.set_page_config(page_title="ReconQ", layout="wide")
init_db()


@st.cache_resource
def get_or_train_model():
    model = load_model()
    if model is None:
        model, _report = train_and_save()
    return model


def _amount_lookup(settlement_path, ledger_path):
    settlements = pd.read_csv(settlement_path, dtype=str, keep_default_na=False)
    ledgers = pd.read_csv(ledger_path, dtype=str, keep_default_na=False)
    s_amt = {r["settlement_id"]: int(r["amount_inr"]) for _, r in settlements.iterrows()}
    s_narr = {r["settlement_id"]: r["narration"] for _, r in settlements.iterrows()}
    l_memo = {r["invoice_id"]: r["memo"] for _, r in ledgers.iterrows()}
    return s_amt, s_narr, l_memo


def run_pipeline(settlement_path, ledger_path):
    model = get_or_train_model()
    with st.status("Running reconciliation pipeline...", expanded=True) as status:
        st.write("Validating input schema...")
        st.write("Exact matching...")
        time.sleep(0.15)
        result = run_reconciliation(settlement_path, ledger_path, model)
        st.write(f"Exact matches: {len(result['matched'])}")
        st.write("Split/merge group detection...")
        time.sleep(0.15)
        st.write(f"Group matches: {len(result['group_matches'])}")
        st.write("Candidate scoring + optimal assignment...")
        time.sleep(0.15)
        st.write(f"Scored pairs: {len(result['assigned'])}")
        st.write("Applying risk-weighted threshold policy...")
        time.sleep(0.15)
        status.update(label="Reconciliation complete.", state="complete")
    for m in result["matched"]:
        append_event(RUN_ID, m["settlement_id"], "system", "EXACT_MATCH", m)
    for gm in result["group_matches"]:
        append_event(RUN_ID, ",".join(gm["settlement_ids"]), "system", "GROUP_MATCH", gm)
    for a in result["assigned"]:
        append_event(RUN_ID, a["settlement_id"], "system", "DECISION",
                      {"invoice_id": a["invoice_id"], "confidence": a["confidence"], "status": a["status"]})
    return result


def kpi_cards(result, s_amt):
    n_auto = len(result["matched"]) + sum(1 for a in result["assigned"] if a["status"] == "AUTO_MATCHED")
    n_review = len(result["group_matches"]) + sum(1 for a in result["assigned"] if a["status"] == "HUMAN_REVIEW")
    n_unresolved = len(result["unresolved_settlements"])
    total_records = n_auto + n_review + n_unresolved
    match_rate = n_auto / total_records if total_records else 0

    auto_ids = [m["settlement_id"] for m in result["matched"]] + \
               [a["settlement_id"] for a in result["assigned"] if a["status"] == "AUTO_MATCHED"]
    rupees_auto = sum(s_amt.get(sid, 0) for sid in auto_ids) / 100
    review_ids = [a["settlement_id"] for a in result["assigned"] if a["status"] == "HUMAN_REVIEW"]
    rupees_review = sum(s_amt.get(sid, 0) for sid in review_ids) / 100

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Match Rate", f"{match_rate:.1%}")
    c2.metric("Rs Auto-Cleared", f"Rs {rupees_auto:,.0f}")
    c3.metric("Rs Routed to Review", f"Rs {rupees_review:,.0f}")
    c4.metric("Exceptions", n_review + n_unresolved)
    c5.metric("Unresolved", n_unresolved)


def record_table(result):
    rows = []
    for m in result["matched"]:
        rows.append({"id": m["settlement_id"], "invoice": m["invoice_id"], "status": m["status"],
                      "confidence": m["confidence"], "type": "exact"})
    for gm in result["group_matches"]:
        rows.append({"id": ",".join(gm["settlement_ids"]), "invoice": ",".join(gm["invoice_ids"]),
                      "status": gm["status"], "confidence": gm["confidence"], "type": gm["match_type"]})
    for a in result["assigned"]:
        rows.append({"id": a["settlement_id"], "invoice": a["invoice_id"], "status": a["status"],
                      "confidence": round(a["confidence"], 3), "type": "1:1"})
    for sid in result["unresolved_settlements"]:
        rows.append({"id": sid, "invoice": "", "status": "UNRESOLVED", "confidence": None, "type": "n/a"})
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", height=350)
    return df


def _group_explanation(gm, s_amt):
    """Evidence-only explanation for a split/merge group -- deterministic, no LLM
    needed since the evidence (which rows sum to which) is already unambiguous."""
    total = sum(s_amt.get(sid, 0) for sid in gm["settlement_ids"]) if gm["match_type"] == "merge" else \
        s_amt.get(gm["settlement_ids"][0], 0)
    return (f"Detected a {gm['match_type']} across {len(gm['settlement_ids'])} settlement row(s) and "
            f"{len(gm['invoice_ids'])} ledger row(s) summing to Rs {total/100:,.2f} within tolerance. "
            f"Routed to human review by policy -- split/merge groups always require a look, "
            f"regardless of confidence.")


def exception_drilldown(result, s_amt, s_narr, l_memo):
    review_items = [a for a in result["assigned"] if a["status"] in ("HUMAN_REVIEW", "UNRESOLVED")]
    group_items = list(result["group_matches"])
    if not review_items and not group_items:
        st.info("No exceptions in this run.")
        return

    pair_labels = [f"1:1  |  {a['settlement_id']} <-> {a['invoice_id']} ({a['status']})" for a in review_items]
    group_labels = [f"SPLIT/MERGE  |  {','.join(gm['settlement_ids'])} <-> {','.join(gm['invoice_ids'])}"
                     for gm in group_items]
    labels = pair_labels + group_labels
    choice = st.selectbox("Select an exception to inspect", labels)
    if not choice:
        return
    idx = labels.index(choice)

    if idx < len(review_items):
        item = review_items[idx]
        evidence = dict(item["features"])
        evidence["amount_inr"] = s_amt.get(item["settlement_id"], 0)
        narration = s_narr.get(item["settlement_id"], "")
        memo = l_memo.get(item["invoice_id"], "")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Settlement side**")
            st.json({"settlement_id": item["settlement_id"], "amount_inr_paise": evidence["amount_inr"],
                      "narration": narration})
        with col2:
            st.write("**Ledger side**")
            st.json({"invoice_id": item["invoice_id"], "memo": memo})

        st.progress(min(max(item["confidence"], 0.0), 1.0), text=f"Confidence: {item['confidence']:.1%}")

        verdict = explain(evidence, narration_a=narration, narration_b=memo)
        st.write("**AI Explanation** " + ("(template fallback)" if verdict.get("source") == "template_fallback" else "(LLM)"))
        st.write(f"Category: `{verdict['category']}`  |  Recommended action: `{verdict['recommended_action']}`")
        st.write(verdict["explanation"])
        if verdict.get("explanation_rejected"):
            st.warning("Original LLM explanation was rejected by the numeric-consistency check and replaced.")
        if verdict.get("injection_marker_detected"):
            st.warning("Injection marker detected in source narration/memo text -- treated as plain data, ignored.")

        bcol1, bcol2 = st.columns(2)
        if bcol1.button("Accept", key=f"accept_{item['settlement_id']}"):
            append_override(RUN_ID, item["settlement_id"], "human:analyst", "accept", "")
            st.success("Recorded: Accepted.")
        if bcol2.button("Override", key=f"override_{item['settlement_id']}"):
            append_override(RUN_ID, item["settlement_id"], "human:analyst", "override", "")
            st.warning("Recorded: Overridden.")
    else:
        gm = group_items[idx - len(review_items)]
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Settlement row(s)**")
            st.json({"settlement_ids": gm["settlement_ids"],
                      "amounts_paise": [s_amt.get(sid, 0) for sid in gm["settlement_ids"]]})
        with col2:
            st.write("**Ledger row(s)**")
            st.json({"invoice_ids": gm["invoice_ids"]})
        st.progress(min(max(gm["confidence"], 0.0), 1.0), text=f"Confidence: {gm['confidence']:.1%}")
        st.write(f"**Match type:** `{gm['match_type']}`  |  **Status:** `{gm['status']}`")
        st.write(_group_explanation(gm, s_amt))

        gid = ",".join(gm["settlement_ids"])
        bcol1, bcol2 = st.columns(2)
        if bcol1.button("Accept", key=f"accept_group_{gid}"):
            append_override(RUN_ID, gid, "human:analyst", "accept", "")
            st.success("Recorded: Accepted.")
        if bcol2.button("Override", key=f"override_group_{gid}"):
            append_override(RUN_ID, gid, "human:analyst", "override", "")
            st.warning("Recorded: Overridden.")


def audit_log_view():
    events = get_all_events(RUN_ID)
    if not events:
        st.info("No audit events yet.")
        return
    df = pd.DataFrame(events)
    st.dataframe(df, width="stretch", height=300)


def main():
    st.title("ReconQ -- Risk-Weighted Reconciliation Agent")
    st.caption("Reconciles settlements against ledgers, raising the auto-clear bar exactly as much "
               "as the money at stake demands.")

    tab1, tab2, tab3, tab4 = st.tabs(["Run", "Decisions", "Exception Drill-Down", "Audit Log"])

    sample_settlement_path = os.path.join(DATA_DIR, "settlement_report.csv")
    sample_ledger_path = os.path.join(DATA_DIR, "internal_ledger.csv")

    with tab1:
        st.write("Upload your own settlement + ledger CSVs, or use the seeded synthetic sample dataset "
                 "(154 settlement rows, 8 labeled mismatch classes).")
        col_up1, col_up2 = st.columns(2)
        settlement_file = col_up1.file_uploader("Settlement report CSV", type="csv", key="settlement_upload")
        ledger_file = col_up2.file_uploader("Internal ledger CSV", type="csv", key="ledger_upload")
        use_sample = st.checkbox("Use sample data instead", value=not (settlement_file and ledger_file))

        if st.button("Run reconciliation", type="primary"):
            if use_sample or not (settlement_file and ledger_file):
                settlement_path, ledger_path = sample_settlement_path, sample_ledger_path
            else:
                tmp_dir = tempfile.mkdtemp(prefix="reconq_upload_")
                settlement_path = os.path.join(tmp_dir, "settlement_report.csv")
                ledger_path = os.path.join(tmp_dir, "internal_ledger.csv")
                with open(settlement_path, "wb") as f:
                    f.write(settlement_file.getvalue())
                with open(ledger_path, "wb") as f:
                    f.write(ledger_file.getvalue())
            try:
                st.session_state["result"] = run_pipeline(settlement_path, ledger_path)
                st.session_state["settlement_path"] = settlement_path
                st.session_state["ledger_path"] = ledger_path
            except SchemaValidationError as exc:
                st.error(f"Input rejected: {exc}")

        if "result" in st.session_state:
            s_amt, _s_narr, _l_memo = _amount_lookup(
                st.session_state["settlement_path"], st.session_state["ledger_path"])
            kpi_cards(st.session_state["result"], s_amt)

    with tab2:
        if "result" in st.session_state:
            df = record_table(st.session_state["result"])
            st.download_button("Export CSV", df.to_csv(index=False), file_name="reconq_decisions.csv")
        else:
            st.info("Run reconciliation first (Run tab).")

    with tab3:
        if "result" in st.session_state:
            s_amt, s_narr, l_memo = _amount_lookup(
                st.session_state["settlement_path"], st.session_state["ledger_path"])
            exception_drilldown(st.session_state["result"], s_amt, s_narr, l_memo)
        else:
            st.info("Run reconciliation first (Run tab).")

    with tab4:
        audit_log_view()


if __name__ == "__main__":
    main()
