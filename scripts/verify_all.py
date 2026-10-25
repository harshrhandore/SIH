"""Evidence-producing sweep. A nonzero step remains a failure in the report."""
import argparse,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(full=False):
    npm='npm.cmd' if os.name=='nt' else 'npm'
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'apps/api'),str(ROOT)]),'PLAYWRIGHT_BROWSERS_PATH':str(ROOT/'.local/browsers'),'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']}
    steps=[('placeholders/secrets',[sys.executable,'scripts/check_placeholders.py']),('schema',[sys.executable,'scripts/check_schema.py']),('python lint',[sys.executable,'-m','ruff','check','--config','apps/api/pyproject.toml','apps/api/app']),('python types',[sys.executable,'-m','mypy','--config-file','apps/api/pyproject.toml','apps/api/app']),('python tests',[sys.executable,'-m','pytest','apps/api/tests','-q']),('web lint',[npm,'run','lint']),('web types',[npm,'run','typecheck']),('web build',[npm,'run','build']),('generated client',[sys.executable,'scripts/check_client.py']),('browser flows',[npm,'run','e2e']),('artifacts',[sys.executable,'scripts/check_artifacts.py']),('benchmark',[sys.executable,'scripts/benchmark.py','--runs','20'])]
    if full:steps.insert(2,('fresh database',[sys.executable,'scripts/reproduce.py']))
    results=[]
    for name,command in steps:
        start=datetime.now(timezone.utc).isoformat()
        r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        results.append(dict(name=name,command=command,start=start,end=datetime.now(timezone.utc).isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        print(f'{name}: '+('PASS' if r.returncode==0 else 'FAIL'),flush=True)
        (ROOT/'docs/verification-results.json').write_text(json.dumps(results,indent=2))
    return int(any(r['exit_code'] for r in results))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');raise SystemExit(run(p.parse_args().full))
