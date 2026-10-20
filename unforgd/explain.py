"""AI explanation on Amazon Bedrock (Claude Opus 4.5, ADR-0006), validated against the code's findings.

The model only explains and drafts; it never decides. Its JSON answer is checked: the liable party, the
clauses and the amount must equal what the rules computed, and every cited evidence ID must exist.
Answers are cached in results/ so the demo also runs without network (marked as cached in the report).
"""
import json
import os
import time
from pathlib import Path

MODEL = os.environ.get("UNFORGD_MODEL", "eu.anthropic.claude-opus-4-5-20251101-v1:0")
FALLBACK_MODEL = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = os.environ.get("AWS_REGION", "eu-central-1")
RESULTS = Path(__file__).resolve().parent.parent / "results"

SYSTEM = ("You are a claims-recovery analyst. You explain findings that deterministic code has already "
          "established; you never change them. Cite evidence only by the IDs given. Answer with JSON only.")


def _prompt(claim, a):
    facts = {
        "claim": {k: claim[k] for k in ("claim_id", "goods", "insurer", "insured", "value_eur", "deductible_eur",
                                       "freight_invoice_eur", "loss")},
        "agreement": claim["agreement"],
        "findings_by_code": {k: a[k] for k in ("liable_role", "liable_party", "clauses", "recoverable_eur",
                                                "payment_decision", "first_broken_step", "altered_documents")},
        "evidence_ids": [d["doc_id"] for d in a["documents"]] + [f"EVENT-{e['seq']}" for e in claim["chain"]],
    }
    schema = ('{"summary": str (3 sentences, plain English), "liable_party": str (must equal findings), '
              '"clauses": [str] (must equal findings), "recoverable_eur": int (must equal findings), '
              '"evidence_ids": [str] (only from evidence_ids), "recovery_letter": str (max 180 words, addressed '
              'to the liable party\'s liability insurer, cites clauses and evidence IDs, states it is '
              'decision support for a human adjuster)}')
    return f"Facts:\n{json.dumps(facts, indent=1)}\n\nReturn JSON with this shape:\n{schema}"


def validate(ans, claim, a):
    ids = {d["doc_id"] for d in a["documents"]} | {f"EVENT-{e['seq']}" for e in claim["chain"]}
    problems = []
    if ans.get("liable_party") != a["liable_party"]:
        problems.append("liable party differs from the code's finding")
    if sorted(ans.get("clauses", [])) != sorted(a["clauses"]):
        problems.append("clauses differ from the code's finding")
    if int(ans.get("recoverable_eur", -1)) != a["recoverable_eur"]:
        problems.append("amount differs from the code's calculation")
    bad = [i for i in ans.get("evidence_ids", []) if i not in ids]
    if bad:
        problems.append(f"unknown evidence IDs cited: {bad}")
    return problems


def explain(claim, a, live=True, profile=None):
    RESULTS.mkdir(exist_ok=True)
    cache = RESULTS / f"{claim['claim_id']}.llm.json"
    if live:
        try:
            import boto3
            session = boto3.Session(profile_name=profile or os.environ.get("AWS_PROFILE"), region_name=REGION)
            client = session.client("bedrock-runtime")
            for model in (MODEL, FALLBACK_MODEL):
                try:
                    t0 = time.time()
                    resp = client.converse(
                        modelId=model, system=[{"text": SYSTEM}],
                        messages=[{"role": "user", "content": [{"text": _prompt(claim, a)}]}],
                        inferenceConfig={"maxTokens": 1200, "temperature": 0})
                    text = resp["output"]["message"]["content"][0]["text"]
                    text = text[text.find("{"): text.rfind("}") + 1]
                    ans = json.loads(text)
                    out = {"source": "live", "model": model, "seconds": round(time.time() - t0, 1),
                           "usage": resp.get("usage", {}), "answer": ans, "validation": validate(ans, claim, a)}
                    cache.write_text(json.dumps(out, indent=1, ensure_ascii=False))
                    return out
                except Exception as e:  # throttling or model access: try the fallback model
                    last = e
            raise last
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:200]}"
            if cache.exists():
                out = json.loads(cache.read_text())
                out["source"] = f"cached (live call failed: {err})"
                return out
            return {"source": f"unavailable ({err})", "model": None, "answer": None,
                    "validation": ["no model answer: run with AWS credentials (see README)"]}
    if cache.exists():
        out = json.loads(cache.read_text())
        out["source"] = "cached"
        return out
    return {"source": "unavailable (offline, no cached answer)", "model": None, "answer": None,
            "validation": ["no model answer: run with AWS credentials (see README)"]}
