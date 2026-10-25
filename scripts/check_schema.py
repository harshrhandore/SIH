"""Independently execute db/schema.sql, compare migrated catalogues, drop only fixed scratch DB."""
import json,os,sys
from pathlib import Path
from urllib.parse import urlparse,urlunparse
import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]

def database_url(url,name):
    parsed=urlparse(url)
    if parsed.hostname not in {'127.0.0.1','localhost','db'} or name not in {'postgres','shiksham_schema_check','shiksham_repro','shiksham_bench_50000','shiksham_bench_100000'}:
        raise RuntimeError('Disposable database target refused')
    return urlunparse(parsed._replace(path='/'+name))

def snapshot(conn):
    queries={
    'objects':"SELECT relname,relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND relname NOT LIKE 'alembic_version%' ORDER BY 1,2",
    'columns':"SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' AND table_name<>'alembic_version' ORDER BY 1,2",
    'constraints':"SELECT cl.relname,c.conname,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_class cl ON cl.oid=c.conrelid JOIN pg_namespace n ON n.oid=cl.relnamespace WHERE n.nspname='public' AND cl.relname<>'alembic_version' ORDER BY 1,2",
    'triggers':"SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2",
    'indexes':"SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename<>'alembic_version' ORDER BY 1,2",
    'functions':"SELECT p.proname,pg_get_function_identity_arguments(p.oid) AS arguments,p.prosecdef,p.proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('append_audit','check_term_integrity','protect_history','refresh_demo_views','lock_audit_chain') ORDER BY 1,2"}
    return {k:conn.execute(q).fetchall() for k,q in queries.items()}

def run():
    owner=os.getenv('DATABASE_OWNER_URL') or dotenv_values(ROOT/'.env')['DATABASE_OWNER_URL']
    with psycopg.connect(database_url(owner,'postgres'),autocommit=True) as c:
        c.execute('DROP DATABASE IF EXISTS shiksham_schema_check WITH (FORCE)');c.execute('CREATE DATABASE shiksham_schema_check')
    try:
        with psycopg.connect(database_url(owner,'shiksham_schema_check'),row_factory=dict_row) as c:
            c.execute((ROOT/'db/schema.sql').read_text(encoding='utf-8-sig'));expected=snapshot(c)
        with psycopg.connect(owner,row_factory=dict_row) as c:
            actual=snapshot(c)
        differences={k:dict(expected=expected[k],actual=actual[k]) for k in expected if expected[k]!=actual[k]}
        (ROOT/'docs/schema-check.json').write_text(json.dumps(dict(equal=not differences,differences=differences),indent=2,default=str))
        print('Schema matches all six catalogues.' if not differences else 'Schema differs: '+','.join(differences))
        return int(bool(differences))
    finally:
        with psycopg.connect(database_url(owner,'postgres'),autocommit=True) as c:c.execute('DROP DATABASE shiksham_schema_check WITH (FORCE)')

if __name__=='__main__':sys.exit(run())
