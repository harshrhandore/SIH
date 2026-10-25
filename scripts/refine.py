"""Apply small source transformations with explicit anchors."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "apps/api/app/main.py"
text = path.read_text()
start = text.index("    allowed={", text.index("@router.patch('/students/{student_id}')"))
end = text.index("\n@router.post('/imports'", start)
text = (
    text[:start]
    + """    from app.modules.students.corrections import correct
    with connect() as conn:
        student_scope(conn,user,student_id,request)
        return idem(conn,user,request,body.model_dump(),lambda key:correct(conn,user,student_id,body))
"""
    + text[end:]
)
text = text.replace("label=l,role=r) for k,e,l,r", "label=label,role=r) for k,e,label,r")
text = text.replace(
    "result=None if request.headers.get('x-demo-cache')=='bypass' else cache.get(key)",
    "result=None if settings.demo_controls_enabled and (request.headers.get('x-demo-cache')=='bypass' or cache.get(('session-controls',str(user['sid']))) is False) else cache.get(key)",
)
path.write_text(text)
