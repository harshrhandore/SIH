"""Check delivered artifacts against the exact supplied repository tree; never create empty substitutes."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def required_paths():
    source=ROOT.parent/'shiksham-apaar-build-prompt-v2.md'
    if not source.exists():return json.loads((ROOT/'docs/required-artifacts.json').read_text())
    spec=source.read_text(encoding='utf-8-sig')
    tree=spec.split('shiksham-apaar/\n',1)[1].split('~~~',1)[0]
    stack=[];required=[]
    for line in tree.splitlines():
        body=line.split('#',1)[0].rstrip()
        if not body.strip():continue
        indent=len(body)-len(body.lstrip())
        while stack and stack[-1][0]>=indent:stack.pop()
        name=body.strip()
        prefix='/'.join(n for _,n in stack)
        if name.endswith('/'):
            stack.append((indent,name[:-1]));continue
        paths=[name]
        if '{' in name:
            begin=name.index('{');end=name.index('}')
            paths=[name[:begin]+part+name[end+1:] for part in name[begin+1:end].split(',')]
        required.extend((prefix+'/'+p).lstrip('/') for p in paths if not p.endswith('/'))
    return required

def run():
    missing=[p for p in required_paths() if not (ROOT/p).exists()]
    manifest=json.loads((ROOT/'fixtures/manifest.json').read_text())
    bad=[name for name,digest in manifest['hashes'].items() if not (ROOT/'fixtures'/name).exists() or hashlib.sha256((ROOT/'fixtures'/name).read_bytes()).hexdigest()!=digest]
    fonts=all((ROOT/'apps/web/public/fonts'/family/'LICENSE').exists() for family in ['fraunces','instrument-sans','ibm-plex-mono'])
    result=dict(missing=missing,bad_fixture_hashes=bad,font_licenses=fonts)
    (ROOT/'docs/artifact-check.json').write_text(json.dumps(result,indent=2))
    print(f'Artifact check: {len(missing)} exact-tree paths absent; {len(bad)} fixture hash mismatches; font licenses present={fonts}.')
    return int(bool(missing or bad or not fonts))

if __name__=='__main__':sys.exit(run())
