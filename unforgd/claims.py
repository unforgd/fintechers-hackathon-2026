"""Synthetic cold-chain claims for the demo and the measured test set.

Everything here is invented (synthetic data only, hackathon rule). A claim has:
- the custody chain registered at the time of each handover (fingerprints of documents and of the raw
  data-logger readings), as Unforgd would record it;
- the dossier submitted later with the insurance claim (documents as presented, possibly altered);
- the ground truth (which party really broke the chain), used only to measure the rules.
"""
import hashlib
import json
import random

RANGE_MIN, RANGE_MAX = 2.0, 8.0          # °C, vaccine cold chain
LEGS = [
    ("manufacturer", "BioVacc NV (Puurs, BE)", "Storage and pick-up at manufacturer"),
    ("carrier", "FrostLine Logistics s.r.o.", "Road transport Puurs → Prague"),
    ("distributor", "MedDistri CZ a.s.", "Receipt and storage at distributor"),
]
AGREEMENT = {
    "id": "MTA-2026-114",
    "title": "Master Transport Agreement BioVacc NV – FrostLine Logistics s.r.o. (synthetic)",
    "clauses": {
        "8.4": ("The Carrier is liable for any loss of or damage to the Goods caused by a temperature excursion "
                "outside 2–8 °C occurring while the Goods are in the Carrier's custody, as evidenced by the "
                "data-logger records registered at pick-up and delivery."),
        "8.6": ("Temperature records submitted by the Carrier must match the data-logger records registered at "
                "the handover; a record that does not match is void as evidence."),
        "11.2": "The Carrier's liability per shipment is limited to EUR 300,000.",
        "12.1": ("Freight invoices for a shipment with an excursion attributable to the Carrier are withheld "
                 "until the claim is settled."),
    },
}


def sha256(data) -> str:
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True, separators=(",", ":"))
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _readings(rng, n, excursion=False):
    vals = [round(rng.uniform(3.2, 6.8), 1) for _ in range(n)]
    if excursion:
        start = rng.randint(n // 4, n // 2)
        for i in range(start, min(n, start + rng.randint(6, 12))):
            vals[i] = round(rng.uniform(9.5, 14.5), 1)
    return vals


def make_claim(claim_id, culprit, alter_log, seed, value=250_000, freight=3_800, deductible=5_000):
    """culprit: None (no excursion) or one of manufacturer/carrier/distributor."""
    rng = random.Random(seed)
    chain, documents, prev = [], {}, "0" * 64
    for i, (role, party, step) in enumerate(LEGS):
        readings = _readings(rng, 48, excursion=(culprit == role))
        log_id = f"{claim_id}-D{i + 1}"
        log_text = "\n".join(f"{t * 15:04d} min  {v:5.1f} °C" for t, v in enumerate(readings))
        documents[log_id] = {"id": log_id, "title": f"Temperature log – {step}", "party": party,
                             "registered_text": log_text, "submitted_text": log_text, "readings": readings}
        event = {"seq": i + 1, "role": role, "party": party, "step": step, "signed_by": party,
                 "time": f"2026-10-1{i + 3}T08:00:00Z",
                 "documents": [{"id": log_id, "sha256": sha256(log_text)}],
                 "readings_sha256": sha256(readings), "prev_hash": prev}
        event["hash"] = sha256({k: v for k, v in event.items() if k != "hash"})
        prev = event["hash"]
        chain.append(event)
    if alter_log:  # the culprit later submits a "clean" log for its own leg
        idx = [r for r, _, _ in LEGS].index(alter_log)
        doc = documents[f"{claim_id}-D{idx + 1}"]
        clean = [min(max(v, 3.4), 7.6) if v > RANGE_MAX else v for v in doc["readings"]]
        doc["submitted_text"] = "\n".join(f"{t * 15:04d} min  {v:5.1f} °C" for t, v in enumerate(clean))
        doc["submitted_readings"] = clean
    return {
        "claim_id": claim_id,
        "goods": "Biologic vaccine, 12 pallets, 2–8 °C (synthetic)",
        "insurer": "Example Cargo Insurance (synthetic)",
        "insured": "Nemocnice Praha (synthetic hospital)",
        "value_eur": value, "deductible_eur": deductible, "freight_invoice_eur": freight,
        "loss": "Goods declared spoiled on arrival; insurer paid the claim and seeks recovery.",
        "agreement": AGREEMENT, "chain": chain, "documents": documents,
        "ground_truth": {"liable": culprit, "altered_log_by": alter_log},
    }


def demo_claim():
    """VAX-001: the carrier breaks the cold chain and submits an altered (clean) temperature log."""
    return make_claim("VAX-001", culprit="carrier", alter_log="carrier", seed=1)


def test_set(n=10):
    cases = [("carrier", "carrier"), ("carrier", None), ("distributor", None), ("manufacturer", None),
             (None, None), ("carrier", "carrier"), ("distributor", "distributor"), (None, None),
             ("manufacturer", "manufacturer"), ("carrier", None)]
    return [make_claim(f"TEST-{i + 1:02d}", c, a, seed=100 + i) for i, (c, a) in enumerate(cases[:n])]
