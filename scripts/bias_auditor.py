import json
import os
from datetime import datetime

def generate_fairness_report():
    log_file = 'bias_log.txt'
    report_dir = 'reports'
    
    if not os.path.exists(log_file):
        print("No bias log found.")
        return

    with open(log_file, 'r') as f:
        logs = f.readlines()

    # Level 3 Logic: Simple Statistical Analysis of Logs
    total_entries = len(logs)
    bias_alerts = [l for l in logs if "WARNING" in l or "BIAS" in l]
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_logs_analyzed": total_entries,
        "bias_incidents": len(bias_alerts),
        "integrity_score": max(0, 100 - (len(bias_alerts) * 5)),
        "status": "PASS" if len(bias_alerts) < 5 else "NEEDS REVIEW"
    }

    # Save to reports folder
    report_path = os.path.join(report_dir, f"fairness_report_{datetime.now().strftime('%Y%m%d')}.json")
    with open(report_path, 'w') as rf:
        json.dump(report_data, rf, indent=4)
    
    print(f"✅ Level 3 Fairness Report generated at: {report_path}")

if __name__ == "__main__":
    generate_fairness_report()