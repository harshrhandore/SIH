"""Explicit preparation of two isolated, allowlisted local benchmark databases."""
import json,os,subprocess,sys
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from check_schema import database_url
ROOT=Path(__file__).resolve().parents[1]
values=dotenv_values(ROOT/'.env')
saved={p:p.read_bytes() for p in (ROOT/'fixtures').rglob('*') if p.is_file()}
reports=[]
try:
    for volume in [50000,100000]:
        name='shiksham_bench_'+str(volume)
        with psycopg.connect(database_url(values['DATABASE_OWNER_URL'],'postgres'),autocommit=True) as c:
            c.execute('DROP DATABASE IF EXISTS '+name+' WITH (FORCE)');c.execute('CREATE DATABASE '+name)
        env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'apps/api'),str(ROOT)]),'DATABASE_OWNER_URL':database_url(values['DATABASE_OWNER_URL'],name),'DATABASE_URL':database_url(values['DATABASE_URL'],name),'STORAGE_ROOT':str(ROOT/'storage'/name)}
        commands=[[sys.executable,'-m','app.cli','bootstrap','--students',str(volume)],[sys.executable,'scripts/benchmark.py','--runs','20','--output',f'docs/benchmark-{volume}.json']]
        for command in commands:
            r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
            reports.append(dict(volume=volume,command=command,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr if r.returncode else ''))
            print(str(volume)+': '+r.stdout.strip(),flush=True)
            if r.returncode:raise RuntimeError('Isolated benchmark step failed: '+r.stderr[-1000:])
finally:
    for p,data in saved.items():p.write_bytes(data)
    (ROOT/'docs/volume-benchmark-results.json').write_text(json.dumps(reports,indent=2))
