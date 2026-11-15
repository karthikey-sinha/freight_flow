"""Process the sample inbox end to end and build the dashboard.

    python run_demo.py            # uses Claude if ANTHROPIC_API_KEY is set, else mock mode
    FREIGHTFLOW_MOCK=1 python run_demo.py
"""
import json

from freightflow import db
from freightflow.config import ROOT, settings
from freightflow.dashboard import build
from freightflow.pipeline import process_email


def main():
    if settings.db_path.exists():
        settings.db_path.unlink()  # fresh run
    emails = json.loads((ROOT / "sample_data" / "emails.json").read_text())
    print(f"Mode: {'MOCK (rule-based)' if settings.mock_mode else settings.provider + ' / ' + settings.model}\n")
    con = db.connect()
    for email in emails:
        r = process_email(email, ROOT / "sample_data" / "docs", con)
        t = r["triage"]
        print(f"[{email['id']}] {t['category']:<16} {t['urgency']:<6} {email['subject'][:55]}")
        for d in r["documents"]:
            f = d["fields"]
            print(f"      doc {d['filename']:<20} {f['doc_type']:<18} weight={f.get('gross_weight_kg')} HS={f.get('hs_codes')}")
        for issue in r["issues"]:
            print(f"      !! {issue}")
        for h in r["history"]:
            print(f"      history: {h}")
        if r["tracking"]:
            print(f"      tracking: {r['tracking']['status']} (ETA {r['tracking']['eta']})")
    con.close()
    print("\nDashboard:", build())
    print("Review drafts with:  python review.py")


if __name__ == "__main__":
    main()
