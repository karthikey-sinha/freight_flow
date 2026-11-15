"""Human-in-the-loop review: approve, edit or reject each AI draft before anything is sent.

    python review.py           # interactive
    python review.py --list    # just show the queue
"""
import sys

from freightflow import db


def main():
    con = db.connect()
    queue = db.pending_drafts(con)
    if not queue:
        print("No drafts waiting for review.")
        return
    for d in queue:
        print("=" * 70)
        print(f"Draft #{d['id']}  [{d['urgency'].upper()}] {d['category']}  from {d['sender']}")
        print(f"Subject: {d['subject']}\nSummary: {d['summary']}\n" + "-" * 70)
        print(d["body"])
        if "--list" in sys.argv:
            continue
        choice = input("\n[a]pprove / [e]dit / [r]eject / [s]kip / [q]uit: ").strip().lower()
        if choice == "a":
            db.review_draft(con, d["id"], "approved")
        elif choice == "e":
            print("Type the new body; finish with a line containing only '.'")
            lines = iter(input, ".")
            db.review_draft(con, d["id"], "approved", body="\n".join(lines))
        elif choice == "r":
            db.review_draft(con, d["id"], "rejected")
        elif choice == "q":
            break
    print("\nDone. Re-run `python -m freightflow.dashboard` to refresh the dashboard.")


if __name__ == "__main__":
    main()
