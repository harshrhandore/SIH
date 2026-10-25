from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'apps/api/app/main.py'
t=p.read_text()
needle='def verify_certificate(certificate_id: UUID, request: Request, user=Depends(authenticated)):'
assert needle in t
t=t.replace(needle,needle+'''
    from app.core.verification_lock import verification_slot
    with verification_slot():
        return verify_certificate_locked(certificate_id,request,user)

def verify_certificate_locked(certificate_id,request,user):''',1)
needle='''        response = certificates.persist_report(conn, certificate, student, result, key, user["id"])'''
assert needle in t
t=t.replace(needle,'''        current=one(conn,'SELECT * FROM certificates WHERE id=%s FOR UPDATE',(certificate_id,))
        prior=one(conn,'SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s',(certificate_id,key))
        if prior:
            return report_response(prior,current)
        fresh=student_scope(conn,user,student['id'],request)
        if fresh['version_no']!=student['version_no']:
            conn.execute("UPDATE certificates SET processing_status='FAILED' WHERE id=%s",(certificate_id,))
            fail('VERSION_CONFLICT',409)
'''+needle,1)
p.write_text(t)
