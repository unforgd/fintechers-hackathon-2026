"""Decision in code: verify the custody chain, locate the break, compute the amount.

The model never decides any of this (AWS Toolbox advice: maths and mandatory rules in code).
"""
from .claims import RANGE_MAX, RANGE_MIN, sha256


def verify_chain(claim):
    """Recompute every event hash and the links between events."""
    prev, problems = "0" * 64, []
    for ev in claim["chain"]:
        body = {k: v for k, v in ev.items() if k != "hash"}
        if ev["prev_hash"] != prev:
            problems.append(f"event {ev['seq']}: link to previous event broken")
        if sha256(body) != ev["hash"]:
            problems.append(f"event {ev['seq']}: event record changed after registration")
        prev = ev["hash"]
    return {"chain_intact": not problems, "problems": problems, "root": prev}


def check_documents(claim):
    """Compare each submitted document with the fingerprint registered at the handover."""
    out = []
    for ev in claim["chain"]:
        for ref in ev["documents"]:
            doc = claim["documents"][ref["id"]]
            submitted = sha256(doc["submitted_text"])
            out.append({"doc_id": ref["id"], "title": doc["title"], "party": doc["party"], "seq": ev["seq"],
                        "registered_sha256": ref["sha256"], "submitted_sha256": submitted,
                        "matches": submitted == ref["sha256"]})
    return out


def excursions(claim):
    """Excursions in the registered data-logger readings (the version that cannot be altered unnoticed)."""
    res = []
    for ev in claim["chain"]:
        doc = claim["documents"][ev["documents"][0]["id"]]
        readings = doc["readings"]
        assert sha256(readings) == ev["readings_sha256"], "registered readings do not match their fingerprint"
        bad = [(i * 15, v) for i, v in enumerate(readings) if v < RANGE_MIN or v > RANGE_MAX]
        res.append({"seq": ev["seq"], "role": ev["role"], "party": ev["party"], "step": ev["step"],
                    "minutes_out_of_range": len(bad) * 15, "max_c": max(readings),
                    "first_minute": bad[0][0] if bad else None, "excursion": bool(bad)})
    return res


def assess(claim):
    chain = verify_chain(claim)
    docs = check_documents(claim)
    exc = excursions(claim)
    broken = next((e for e in exc if e["excursion"]), None)
    altered = [d for d in docs if not d["matches"]]
    liable = broken["role"] if broken else None
    clauses = []
    amount = 0
    if liable == "carrier":
        clauses = ["8.4", "11.2"] + (["8.6"] if any(d["party"] == broken["party"] for d in altered) else [])
        amount = min(claim["value_eur"] - claim["deductible_eur"], 300_000)
    elif liable in ("manufacturer", "distributor"):
        clauses = []  # outside the carrier agreement: the insurer recovers from that party under its own contract
        amount = claim["value_eur"] - claim["deductible_eur"]
    decision = {
        "freight_invoice_eur": claim["freight_invoice_eur"],
        "freight_payment": "WITHHOLD (clause 12.1)" if liable == "carrier" else "RELEASE",
    }
    return {
        "claim_id": claim["claim_id"], "chain": chain, "documents": docs, "excursions": exc,
        "first_broken_step": broken, "altered_documents": altered,
        "liable_role": liable, "liable_party": broken["party"] if broken else None,
        "clauses": clauses, "recoverable_eur": amount, "payment_decision": decision,
        "human_review": bool(altered) or liable is None,
    }


def measure(claims):
    """Share of test claims where the rules name the party that really broke the chain."""
    rows = []
    for c in claims:
        a = assess(c)
        rows.append({"claim_id": c["claim_id"], "expected": c["ground_truth"]["liable"],
                     "found": a["liable_role"], "altered_found": [d["party"] for d in a["altered_documents"]],
                     "ok": a["liable_role"] == c["ground_truth"]["liable"]})
    return {"correct": sum(r["ok"] for r in rows), "total": len(rows), "rows": rows}
