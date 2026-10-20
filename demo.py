#!/usr/bin/env python3
"""Unforgd demo: who pays when the cold chain breaks?

  python3 demo.py                 # offline: rules + cached AI answer + report
  python3 demo.py --live          # also calls Claude Opus 4.5 on Amazon Bedrock (AWS_PROFILE, eu-central-1)
  python3 demo.py --live --profile hackathon
"""
import argparse
import json
import webbrowser
from pathlib import Path

from unforgd.claims import demo_claim, test_set
from unforgd.explain import explain
from unforgd.report import render
from unforgd.rules import assess, measure

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true", help="call Amazon Bedrock")
    p.add_argument("--profile", default=None, help="AWS profile (default: AWS_PROFILE)")
    p.add_argument("--no-open", action="store_true")
    args = p.parse_args()

    claim = demo_claim()
    a = assess(claim)
    print(f"Claim {claim['claim_id']}: chain intact={a['chain']['chain_intact']}  root={a['chain']['root'][:16]}…")
    for d in a["documents"]:
        print(f"  {d['doc_id']:10} {d['party']:32} {'OK' if d['matches'] else 'ALTERED'}")
    print(f"  first broken step: {a['first_broken_step']['party'] if a['first_broken_step'] else '-'}")
    print(f"  liable: {a['liable_party']}  clauses {a['clauses']}  recoverable EUR {a['recoverable_eur']:,}")
    print(f"  freight invoice: {a['payment_decision']['freight_payment']}")

    m = measure(test_set())
    print(f"Measured: {m['correct']}/{m['total']} test claims, liable party found correctly")

    anchor = None
    anchor_file = ROOT / "results" / f"{claim['claim_id']}.anchor.json"
    if anchor_file.exists():
        anchor = json.loads(anchor_file.read_text())
        anchor["matches"] = anchor.get("root") == a["chain"]["root"]

    ai = explain(claim, a, live=args.live, profile=args.profile)
    print(f"AI: {ai.get('source')} · model {ai.get('model')} · check: {ai.get('validation') or 'consistent'}")

    out = render(claim, a, ai, m, anchor)
    print(f"Report: {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
