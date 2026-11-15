"""Accuracy test against hand-labelled ground truth (sample_data/ground_truth.json).

    python evaluate.py
Prints classification accuracy, urgency accuracy and field-level extraction accuracy.
Run it in mock mode and Claude mode to show the improvement the LLM brings.
"""
import json

from freightflow.config import ROOT, settings
from freightflow.documents import extract
from freightflow.emails import triage


def same(a, b):
    if isinstance(b, list):
        return sorted(a or []) == sorted(b)
    if isinstance(b, (int, float)) and a is not None:
        try:
            return abs(float(a) - b) < 0.01
        except (TypeError, ValueError):
            return False
    return str(a).strip().upper() == str(b).strip().upper()


def main():
    gt = json.loads((ROOT / "sample_data" / "ground_truth.json").read_text())
    emails = {e["id"]: e for e in json.loads((ROOT / "sample_data" / "emails.json").read_text())}
    print(f"Mode: {'MOCK' if settings.mock_mode else settings.provider + ' / ' + settings.model}\n")

    cat_ok = urg_ok = 0
    for eid, truth in gt["emails"].items():
        t = triage(emails[eid])
        c, u = t["category"] == truth["category"], t["urgency"] == truth["urgency"]
        cat_ok += c
        urg_ok += u
        if not (c and u):
            print(f"  {eid}: got {t['category']}/{t['urgency']}, expected {truth['category']}/{truth['urgency']}")
    n = len(gt["emails"])
    print(f"Email category accuracy: {cat_ok}/{n} = {cat_ok / n:.0%}")
    print(f"Urgency accuracy:        {urg_ok}/{n} = {urg_ok / n:.0%}\n")

    ok = total = 0
    for fname, truth in gt["documents"].items():
        got = extract(ROOT / "sample_data" / "docs" / fname)
        for field, expected in truth.items():
            total += 1
            if same(got.get(field), expected):
                ok += 1
            else:
                print(f"  {fname}.{field}: got {got.get(field)!r}, expected {expected!r}")
    print(f"Document field accuracy: {ok}/{total} = {ok / total:.0%}")


if __name__ == "__main__":
    main()
