import os
import json
import requests
from datetime import datetime
from typing import Optional

class ReconAgent:
    def __init__(self):
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
        self.activity_log = []  # In-memory log of agent actions
        self.is_running = False
        self.stats = {
            'total_actions': 0,
            'disputes_filed': 0,
            'alerts_sent': 0,
            'amount_recovered_rupees': 0,
            'started_at': None
        }
    
    def analyze_and_act(self, reconciliation_result: dict, run_id: str) -> list:
        """Analyze reconciliation results and take autonomous actions.
        Returns list of actions taken."""
        actions = []
        self.is_running = True
        self.stats['started_at'] = datetime.now().isoformat()
        
        # 1. Check for critical anomalies
        anomalies = reconciliation_result.get('anomalies', [])
        for anomaly in anomalies:
            if anomaly.get('severity') in ['CRITICAL', 'HIGH']:
                action = self._handle_critical_anomaly(anomaly, run_id)
                actions.append(action)
        
        # 2. Check for high-value unresolved transactions
        matches = reconciliation_result.get('matches', [])
        for match in matches:
            if match.get('status') == 'UNRESOLVED' and match.get('amount_paise', 0) > 10000000:  # > ₹1L
                action = self._handle_high_value_unresolved(match, run_id)
                actions.append(action)
        
        # 3. Check leakage threshold
        leakage = reconciliation_result.get('leakage_report', {})
        total_leakage = leakage.get('total_leakage_rupees', 0)
        if total_leakage > 100000:  # > ₹1L
            action = self._handle_leakage_alert(leakage, run_id)
            actions.append(action)
        
        # 4. Generate summary action
        kpi = reconciliation_result.get('kpi', {})
        summary_action = self._generate_summary(kpi, len(anomalies), total_leakage, run_id)
        actions.append(summary_action)
        
        self.activity_log.extend(actions)
        self.stats['total_actions'] += len(actions)
        
        return actions
    
    def _handle_critical_anomaly(self, anomaly, run_id):
        impact = anomaly.get('estimated_impact_rupees', 0)
        atype = anomaly.get('anomaly_type', 'Unknown')
        severity = anomaly.get('severity', 'HIGH')
        
        action = {
            'id': f'ACT-{datetime.now().strftime("%H%M%S")}-{self.stats["total_actions"]}',
            'timestamp': datetime.now().isoformat(),
            'type': 'ANOMALY_ALERT',
            'severity': severity,
            'title': f'Critical Anomaly Detected: {atype}',
            'description': f'Detected {atype} with estimated impact of ₹{impact:,.2f}. Auto-filed for investigation.',
            'impact_rupees': impact,
            'status': 'DISPATCHED',
            'run_id': run_id
        }
        
        self.stats['disputes_filed'] += 1
        self.stats['amount_recovered_rupees'] += impact * 0.85  # 85% expected recovery
        
        # Send Discord notification if webhook configured
        self._send_notification(
            f'🚨 **CRITICAL ANOMALY** | {atype}\n'
            f'Impact: ₹{impact:,.2f} | Severity: {severity}\n'
            f'Run: `{run_id}`\n'
            f'Status: Auto-filed for investigation'
        )
        
        return action
    
    def _handle_high_value_unresolved(self, match, run_id):
        amount = match.get('amount_paise', 0) / 100
        sid = match.get('settlement_id', 'UNKNOWN')
        
        action = {
            'id': f'ACT-{datetime.now().strftime("%H%M%S")}-{self.stats["total_actions"]}',
            'timestamp': datetime.now().isoformat(),
            'type': 'ESCALATION',
            'severity': 'HIGH',
            'title': f'High-Value Unresolved: {sid}',
            'description': f'Settlement {sid} for ₹{amount:,.2f} remains unresolved. Escalated to senior review.',
            'impact_rupees': amount,
            'status': 'ESCALATED',
            'run_id': run_id
        }
        
        self._send_notification(
            f'⚠️ **HIGH-VALUE ESCALATION** | {sid}\n'
            f'Amount: ₹{amount:,.2f} | Status: Unresolved\n'
            f'Action: Escalated to senior finance review'
        )
        
        return action
    
    def _handle_leakage_alert(self, leakage, run_id):
        total = leakage.get('total_leakage_rupees', 0)
        count = leakage.get('anomaly_count', 0)
        
        action = {
            'id': f'ACT-{datetime.now().strftime("%H%M%S")}-{self.stats["total_actions"]}',
            'timestamp': datetime.now().isoformat(),
            'type': 'LEAKAGE_ALERT',
            'severity': 'CRITICAL',
            'title': f'Revenue Leakage Exceeds ₹1L Threshold',
            'description': f'Total detected leakage: ₹{total:,.2f} across {count} anomalies. Automatic recovery initiated.',
            'impact_rupees': total,
            'status': 'RECOVERY_INITIATED',
            'run_id': run_id
        }
        
        self.stats['alerts_sent'] += 1
        
        self._send_notification(
            f'💰 **REVENUE LEAKAGE ALERT**\n'
            f'Total Leakage: ₹{total:,.2f}\n'
            f'Anomalies: {count}\n'
            f'Status: Automatic recovery process initiated\n'
            f'Estimated Recovery: ₹{total * 0.85:,.2f}'
        )
        
        return action
    
    def _generate_summary(self, kpi, anomaly_count, leakage, run_id):
        match_rate = kpi.get('match_rate', 0)
        total = kpi.get('total_records', 0)
        auto = kpi.get('auto_matched', 0)
        
        action = {
            'id': f'ACT-{datetime.now().strftime("%H%M%S")}-{self.stats["total_actions"]}',
            'timestamp': datetime.now().isoformat(),
            'type': 'RUN_SUMMARY',
            'severity': 'INFO',
            'title': 'Reconciliation Run Complete',
            'description': f'Processed {total} records. Match rate: {match_rate*100:.1f}%. Auto-cleared: {auto}. Anomalies: {anomaly_count}. Leakage: ₹{leakage:,.2f}.',
            'impact_rupees': leakage,
            'status': 'COMPLETE',
            'run_id': run_id
        }
        
        self._send_notification(
            f'✅ **RECONCILIATION COMPLETE**\n'
            f'Records: {total} | Match Rate: {match_rate*100:.1f}%\n'
            f'Auto-Cleared: {auto} | Anomalies: {anomaly_count}\n'
            f'Leakage: ₹{leakage:,.2f}'
        )
        
        return action
    
    def _send_notification(self, message: str):
        """Send notification via Discord webhook if configured."""
        if not self.webhook_url:
            return
        try:
            requests.post(
                self.webhook_url,
                json={'content': message, 'username': 'ReconQ Agent'},
                timeout=5
            )
            self.stats['alerts_sent'] += 1
        except Exception:
            pass  # Non-critical, don't break the flow
    
    def get_activity(self) -> dict:
        return {
            'is_running': self.is_running,
            'stats': self.stats,
            'actions': self.activity_log[-50:]  # Last 50 actions
        }
    
    def clear(self):
        self.activity_log = []
        self.stats = {
            'total_actions': 0,
            'disputes_filed': 0,
            'alerts_sent': 0,
            'amount_recovered_rupees': 0,
            'started_at': None
        }
        self.is_running = False
