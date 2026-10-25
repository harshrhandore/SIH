"""Isolated 200-student crash/resume regression; fixed scratch database only."""
import json,os,subprocess,sys
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from check_schema import database_url
ROOT=Path(__file__).resolve().parents[1]
values=dotenv_values(ROOT/'.env')
url=database_url(values['DATABASE_OWNER_URL'],'shiksham_repro')
if '--worker' not in sys.argv:
    saved={p:p.read_bytes() for p in (ROOT/'fixtures').rglob('*') if p.is_file()}
    with psycopg.connect(database_url(values['DATABASE_OWNER_URL'],'postgres'),autocommit=True) as c:
        c.execute('DROP DATABASE IF EXISTS shiksham_repro WITH (FORCE)');c.execute('CREATE DATABASE shiksham_repro')
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'apps/api'),str(ROOT)]),'DATABASE_OWNER_URL':url,'DATABASE_URL':database_url(values['DATABASE_URL'],'shiksham_repro'),'STORAGE_ROOT':str(ROOT/'storage/repro')}
    bootstrap=subprocess.run([sys.executable,'-m','app.cli','bootstrap','--students','200'],cwd=ROOT,env=env,capture_output=True,text=True)
    if bootstrap.returncode:
        for p,data in saved.items():p.write_bytes(data)
        print(bootstrap.stderr);raise SystemExit(bootstrap.returncode)
    result=subprocess.run([sys.executable,__file__,'--worker'],cwd=ROOT,env=env,capture_output=True,text=True)
    print(result.stdout);print(result.stderr if result.returncode else '')
    for p,data in saved.items():p.write_bytes(data)
    raise SystemExit(result.returncode)
from app.db.session import connect,one
from app.modules.imports import service
from app.core.audit import verify
from db.seed.fixtures import uid
from uuid import uuid4
from psycopg.types.json import Jsonb
with connect() as c:
    user=one(c,'SELECT * FROM users WHERE id=%s',(uid('user','operator_a'),))
    data=(ROOT/'fixtures/demo-import-1000.csv').read_bytes()
    uploaded=service.upload(c,user,data,'demo-import-1000.csv',uuid4())
    bid=uploaded['batch_id']
    c.execute("UPDATE import_batches SET status='MAPPED',column_mapping=%s WHERE id=%s",(Jsonb(dict(mapping=service.ALIASES,date_format='DD/MM/YYYY')),bid))
    job=service.start(c,one(c,'SELECT * FROM import_batches WHERE id=%s',(bid,)))
try:service.process(job,fail_after=500)
except RuntimeError as e:assert str(e)=='TEST_INTERRUPTION'
with connect() as c:
    state=one(c,'SELECT * FROM import_jobs WHERE id=%s',(job,))
    assert state['status']=='FAILED' and state['next_row']==501
    assert one(c,'SELECT count(*) AS n FROM import_rows WHERE batch_id=%s AND student_id IS NOT NULL',(bid,))['n']==500
    c.execute("UPDATE import_jobs SET status='QUEUED',retry_count=retry_count+1 WHERE id=%s",(job,))
service.process(job)
with connect() as c:
    report=service.report(c,bid)
    assert tuple(report[k] for k in ['clean','flagged','incomplete','all_findings'])==(880,110,10,140),report
    assert one(c,"SELECT count(*) AS n FROM review_cases WHERE status<>'APPROVED'")['n']==120
    assert one(c,'SELECT count(*) AS n FROM duplicate_candidates')['n']==50
    assert one(c,"SELECT count(*) AS n FROM audit_events WHERE action='STUDENT_IMPORTED'")['n']==1000
    assert one(c,'SELECT count(*) AS n FROM record_versions')['n']==1200
    assert verify(c,uid('institution',0))['valid']
result=dict(crashed_after=500,resumed_at=501,student_import_events=1000,versions=1200,candidates=50,open_cases=120,report=report)
(ROOT/'docs/fault-rehearsal-results.json').write_text(json.dumps(result,indent=2,default=str))
print(json.dumps(result,default=str))
