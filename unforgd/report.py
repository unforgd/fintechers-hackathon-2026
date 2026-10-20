"""One-page HTML report for the demo screen."""
import html
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _e(x):
    return html.escape(str(x))


def render(claim, a, ai, measured, anchor=None):
    exc_rows = "".join(
        f"<tr class='{'bad' if e['excursion'] else 'ok'}'><td>{e['seq']}</td><td>{_e(e['party'])}</td>"
        f"<td>{_e(e['step'])}</td><td>{'⚠ ' + str(e['minutes_out_of_range']) + ' min out of 2–8 °C, max ' + str(e['max_c']) + ' °C' if e['excursion'] else 'in range'}</td></tr>"
        for e in a["excursions"])
    doc_rows = "".join(
        f"<tr class='{'ok' if d['matches'] else 'bad'}'><td>{_e(d['doc_id'])}</td><td>{_e(d['title'])}</td>"
        f"<td><code>{d['registered_sha256'][:16]}…</code></td><td><code>{d['submitted_sha256'][:16]}…</code></td>"
        f"<td>{'✔ matches' if d['matches'] else '✘ ALTERED after registration'}</td></tr>" for d in a["documents"])
    ans = ai.get("answer") or {}
    val = ai.get("validation") or []
    ai_block = (f"<p>{_e(ans.get('summary', ''))}</p><h3>Draft recovery letter</h3><pre>{_e(ans.get('recovery_letter', ''))}</pre>"
                if ans else "<p><em>No model answer available.</em></p>")
    anchor_block = ""
    if anchor:
        status = "✔ log root matches the on-chain anchor" if anchor.get("matches") else "✘ log root does NOT match the anchor"
        anchor_block = (f"<h2>Public anchor (Solana devnet)</h2><p>{status}. Transaction: "
                        f"<a href='{_e(anchor['explorer'])}'>{_e(anchor['signature'][:24])}…</a></p>")
    m = measured
    html_doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Unforgd · {claim['claim_id']}</title>
<style>body{{font-family:-apple-system,Segoe UI,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;margin:8px 0 16px}}td,th{{border:1px solid #ddd;padding:6px 8px;text-align:left;font-size:14px}}
tr.bad{{background:#fde8e8}}tr.ok{{background:#eefaf0}}.big{{font-size:20px;font-weight:600}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:12px}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;background:#eee;font-size:12px}}</style></head><body>
<h1>Unforgd · liability check · {_e(claim['claim_id'])}</h1>
<p>{_e(claim['goods'])} · insured value EUR {claim['value_eur']:,} · {_e(claim['loss'])} <span class="tag">synthetic data</span></p>
<h2>1. Custody chain (registered at each handover)</h2>
<p>Chain {'✔ intact: every event hash and link verified' if a['chain']['chain_intact'] else '✘ ' + '; '.join(a['chain']['problems'])} · root <code>{a['chain']['root'][:20]}…</code></p>
<table><tr><th>#</th><th>Custodian</th><th>Step</th><th>Registered data-logger readings</th></tr>{exc_rows}</table>
<h2>2. Submitted documents vs registered fingerprints</h2>
<table><tr><th>ID</th><th>Document</th><th>Registered SHA-256</th><th>Submitted SHA-256</th><th>Result</th></tr>{doc_rows}</table>
{anchor_block}
<h2>3. Decision (computed in code)</h2>
<p class="big">Liable: {_e(a['liable_party'] or 'no party (no excursion)')} · recoverable EUR {a['recoverable_eur']:,} · clauses {_e(', '.join(a['clauses']) or '–')}</p>
<p>Freight invoice EUR {a['payment_decision']['freight_invoice_eur']:,}: <strong>{_e(a['payment_decision']['freight_payment'])}</strong> · human review required: {'yes' if a['human_review'] else 'no'}</p>
<h2>4. Explanation by AI <span class="tag">{_e(ai.get('model') or '-')}</span> <span class="tag">{_e(ai.get('source'))}</span></h2>
<p>Check against the code: {'✔ consistent' if not val else '✘ ' + _e('; '.join(val))}</p>
{ai_block}
<h2>5. Measured</h2>
<p class="big">The rules named the right party in {m['correct']} of {m['total']} synthetic claims.</p>
<p><em>Decision support for a human adjuster, not a verdict. Fingerprints prove a record was not changed and who
registered it; they do not prove the record was true when registered.</em></p>
</body></html>"""
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{claim['claim_id']}.html"
    out.write_text(html_doc)
    (RESULTS / f"{claim['claim_id']}.assessment.json").write_text(json.dumps(a, indent=1, ensure_ascii=False))
    return out
