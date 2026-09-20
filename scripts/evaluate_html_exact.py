"""Minimal auditable HTML exact-match (Acc-Con) evaluator for PubTables-v2 JSON."""
import argparse, json, re
from pathlib import Path

def norm(s):
    s=re.sub(r"\\s+", " ", s or "").strip().lower()
    return s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('predictions', type=Path); ap.add_argument('truth_dir', type=Path); ap.add_argument('--output', type=Path, required=True); a=ap.parse_args()
    pred=json.loads(a.predictions.read_text())
    rows=[]
    for k,v in pred.items():
        truth=None
        for f in a.truth_dir.glob('*.json'):
            try:
                for t in json.loads(f.read_text()):
                    if str(t.get('id',t.get('table_id',''))) == k: truth=t
            except Exception: pass
        gt=norm(truth.get('html') if truth else '') if truth else ''
        pr=norm(v.get('html','') if isinstance(v,dict) else v)
        rows.append({'id':k,'exact':bool(gt and pr and gt==pr),'truth_found':truth is not None})
    out={'count':len(rows),'truth_found':sum(x['truth_found'] for x in rows),'Acc-Con':sum(x['exact'] for x in rows)/len(rows) if rows else 0.0,'rows':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)); print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__': main()
