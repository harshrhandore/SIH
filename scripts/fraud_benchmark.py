"""Synthetic sanity check only; no real-world accuracy claim."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'apps/api'),str(ROOT)]
from db.seed.fixtures import pdf_bytes
from app.modules.certificates.service import evaluate
from app.core.weights import load_weights

matrix=dict(true_positive=0,false_positive=0,true_negative=0,false_negative=0)
samples=[]
for tampered in [False,True]:
    for index in range(30):
        data=pdf_bytes(name='Kunal Mehta' if tampered else 'Riya Sharma',title=f'Synthetic course {index+1}',credential=f'SYNDS-{index+1:04d}',tampered=tampered)
        result=evaluate(data,'application/pdf',dict(full_name='Riya Sharma',dob='2004-06-15'))
        flagged=result['risk']['score']>=60
        key='true_positive' if tampered and flagged else 'false_negative' if tampered else 'false_positive' if flagged else 'true_negative'
        matrix[key]+=1
        samples.append(dict(tampered=tampered,score=result['risk']['score'],codes=[r['code'] for r in result['risk']['reasons']]))
result=dict(label='Synthetic sanity check; not accuracy on real certificates',seed=2026263,confusion_matrix=matrix,weights=load_weights('fraud'),samples=samples)
(ROOT/'docs/fraud-benchmark.json').write_text(json.dumps(result,indent=2))
print(json.dumps(matrix))
