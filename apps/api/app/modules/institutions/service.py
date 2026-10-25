from app.core.security import allow, institution_scope, scope_ids
from app.core.errors import fail
from app.db.session import connect
from app.modules.institutions import repository


def institutions(user, state):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    scope = institution_scope(user, admin=True)
    with connect() as conn:
        if state is not None and not repository.known_state(conn, state):
            fail("UNKNOWN_STATE", 422, "Choose a state represented in the synthetic catalogue.")
        rows = repository.scoped_institutions(conn, scope, state)
    return dict(items=rows, total=len(rows), page=1, page_size=25)


def programs(user, institution_id):
    allow(user, "OPERATOR", "OFFICER", "ADMIN", "STUDENT")
    if user["role_code"] != "ADMIN" and institution_id not in scope_ids(user):
        fail("NOT_FOUND", 404)
    with connect() as conn:
        if not repository.institution_exists(conn, institution_id):
            fail("NOT_FOUND", 404)
        rows = repository.institution_programs(conn, institution_id)
    return dict(items=rows, total=len(rows), page=1, page_size=25)
