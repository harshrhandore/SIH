from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
from fastapi.testclient import TestClient
import psycopg
import pytest
from app.main import app
from app.settings import ROOT
from app.db.session import connect,one
from app.cli import owner_url
from app.core.audit import append,verify
from db.seed.fixtures import uid

client=TestClient(app)

def login(email):
    r=client.post('/api/v1/auth/login',json={'email':email,'password':dotenv_values(ROOT/'.env')['DEMO_PASSWORD']})
    assert r.status_code==200,r.text
    value=r.json()
    return value,{'Authorization':'Bearer '+value['access_token'],'X-CSRF-Token':value['csrf_token'],'Idempotency-Key':str(uuid4())}

def test_runtime_immutable_privileges():
    for statement in ['UPDATE audit_events SET reason=reason','DELETE FROM audit_events WHERE false','TRUNCATE audit_events','UPDATE audit_chains SET head_seq=head_seq','DELETE FROM record_versions WHERE false','UPDATE review_decisions SET reason=reason']:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with connect() as conn:
                conn.execute(statement)

def test_scope_and_forged_token():
    _,operator=login('operator.b@example.test')
    sid=str(uid('student',1));institution=str(uid('institution',0))
    for path in ['/students/'+sid,'/students/'+sid+'/trust','/students/'+sid+'/versions','/students/'+sid+'/timeline','/students/'+sid+'/career/history']:
        assert client.get('/api/v1'+path,headers=operator).status_code==404
    assert client.get('/api/v1/students/search?institution_id='+institution,headers=operator).status_code==403
    assert client.get('/api/v1/auth/me',headers={'Authorization':operator['Authorization']+'x'}).status_code==401
    _,student=login('student.riya@example.test')
    assert client.get('/api/v1/students/'+str(uid('student',2)),headers=student).status_code==404
    _,admin=login('admin@example.test')
    assert client.get('/api/v1/students/'+sid,headers=admin).status_code==404
    rows=client.get('/api/v1/cases',headers=admin).json()['items']
    assert all('student_id' not in r and 'full_name' not in r and 'dob' not in r and 'email' not in r for r in rows)

def test_refresh_reuse_revokes_family():
    value,headers=login('operator.a@example.test')
    r=client.post('/api/v1/auth/refresh',headers=headers,json={'refresh_token':value['refresh_token']})
    assert r.status_code==200
    fresh=r.json()
    assert client.post('/api/v1/auth/refresh',headers=headers,json={'refresh_token':value['refresh_token']}).status_code==401
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+fresh['access_token']}).status_code==401

def test_csrf_and_origin():
    _,headers=login('student.riya@example.test')
    headers.pop('X-CSRF-Token')
    assert client.post('/api/v1/auth/logout',headers=headers,json={}).status_code==403
    assert client.post('/api/v1/auth/login',headers={'Origin':'https://invalid.example.test'},json={'email':'a','password':'b'}).status_code==403

def test_concurrent_audit_appends():
    institution=uid('institution',1)
    def write(i):
        with connect() as conn:
            append(conn,institution,uid('user','officer'),'AUDIT_CONCURRENCY_TEST','institution',institution,'Synthetic concurrency regression check.',{'index':i})
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write,range(100)))
    with connect() as conn:
        result=verify(conn,institution)
        assert result['valid'] and result['events_checked']>=101

def test_term_guard():
    with pytest.raises(psycopg.errors.RaiseException,match='ENROLMENT_MISMATCH'):
        with connect() as conn:
            conn.execute("INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) SELECT %s,id,2022,1,'SEMESTER',22,8,8 FROM enrolments WHERE student_id=%s LIMIT 1",(uid('student',2),uid('student',1)))
