from app.db.session import many, one


def institution_exists(conn, institution_id):
    return one(conn, "SELECT 1 FROM institutions WHERE id=%s", (institution_id,)) is not None


def known_state(conn, state):
    return one(conn, "SELECT 1 FROM institutions WHERE state=%s LIMIT 1", (state,)) is not None


def scoped_institutions(conn, institution_ids, state):
    return many(
        conn,
        "SELECT id,name,state,aicte_code FROM institutions WHERE (%s::uuid[] IS NULL OR id=ANY(%s::uuid[])) AND (%s::text IS NULL OR state=%s) ORDER BY name,id",
        (institution_ids, institution_ids, state, state),
    )


def institution_programs(conn, institution_id):
    return many(conn, "SELECT * FROM programs WHERE institution_id=%s ORDER BY name,id", (institution_id,))
