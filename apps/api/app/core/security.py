import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from passlib.hash import bcrypt
from fastapi import Request
from app.core.errors import fail
from app.db.session import connect, one, many
from app.settings import settings


def hash_token(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    if len(value.encode()) > 72:
        fail("PASSWORD_TOO_LONG")
    return bcrypt.using(rounds=12).hash(value)


def password_ok(value, encoded):
    return len(value.encode()) <= 72 and bcrypt.verify(value, encoded)


def issue(conn, user, family=None):
    now = datetime.now(timezone.utc)
    family = family or uuid4()
    refresh, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO refresh_sessions(user_id,family_id,token_hash,csrf_hash,expires_at) VALUES (%s,%s,%s,%s,%s)",
        (user["id"], family, hash_token(refresh), hash_token(csrf), now + timedelta(days=7)),
    )
    token = jwt.encode(
        dict(
            sub=str(user["id"]),
            role=user["role_code"],
            sid=str(family),
            iat=now,
            exp=now + timedelta(minutes=15),
            jti=str(uuid4()),
            iss="shiksham-apaar",
            aud="shiksham-web",
        ),
        settings.jwt_secret,
        algorithm="HS256",
    )
    return dict(
        access_token=token,
        refresh_token=refresh,
        csrf_token=csrf,
        token_type="bearer",
        expires_in=900,
        user=public_user(conn, user),
    )


def public_user(conn, user):
    return {
        **{k: user.get(k) for k in ["id", "email", "full_name", "institution_id", "student_id"]},
        "role": user["role_code"],
        "assigned_institutions": [
            r["institution_id"]
            for r in many(conn, "SELECT institution_id FROM user_institutions WHERE user_id=%s", (user["id"],))
        ],
    }


def authenticated(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        fail("UNAUTHENTICATED", 401)
    try:
        claims = jwt.decode(
            auth[7:],
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer="shiksham-apaar",
            audience="shiksham-web",
            options={"require": ["sub", "sid", "iat", "exp", "jti"]},
        )
    except jwt.InvalidTokenError:
        fail("UNAUTHENTICATED", 401)
    with connect() as conn:
        user = one(conn, "SELECT * FROM users WHERE id=%s AND active", (claims["sub"],))
        if not user:
            fail("UNAUTHENTICATED", 401)
        session = one(
            conn,
            "SELECT * FROM refresh_sessions WHERE family_id=%s AND user_id=%s AND revoked_at IS NULL AND rotated_at IS NULL AND expires_at>now()",
            (claims["sid"], user["id"]),
        )
        if not session:
            fail("UNAUTHENTICATED", 401)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if hash_token(request.headers.get("x-csrf-token", "")) != session["csrf_hash"]:
                fail("CSRF_INVALID", 403)
        user["assigned_institutions"] = [
            r["institution_id"]
            for r in many(conn, "SELECT institution_id FROM user_institutions WHERE user_id=%s", (user["id"],))
        ]
        user["sid"] = claims["sid"]
    request.state.user = user
    return user


def allow(user, *roles):
    if user["role_code"] not in roles:
        fail("CAPABILITY_FORBIDDEN", 403)


def scope_ids(user):
    if user["role_code"] in {"OPERATOR", "STUDENT"}:
        return [user["institution_id"]]
    return user["assigned_institutions"] if user["role_code"] == "OFFICER" else []


def institution_scope(user, institution_id=None, admin=False):
    if admin and user["role_code"] == "ADMIN":
        return [institution_id] if institution_id else None
    ids = scope_ids(user)
    if institution_id and str(institution_id) not in {str(i) for i in ids}:
        fail("SCOPE_FILTER_FORBIDDEN", 403)
    return [institution_id] if institution_id else ids


def student_scope(conn, user, student_id, request=None):
    student = one(
        conn,
        "SELECT s.*,p.name AS program,p.branch,p.total_terms,p.duration_years,p.term_type,i.name AS institution_name FROM students s LEFT JOIN programs p ON p.id=s.program_id JOIN institutions i ON i.id=s.institution_id WHERE s.id=%s",
        (student_id,),
    )
    if not student:
        fail("NOT_FOUND", 404)
    role = user["role_code"]
    permitted = role in {"OPERATOR", "OFFICER"} and student["institution_id"] in scope_ids(user)
    permitted = permitted or role == "STUDENT" and student["id"] == user["student_id"]
    if role == "ADMIN" and request:
        try:
            grant = jwt.decode(
                request.headers.get("x-case-access", ""),
                settings.grant_secret,
                algorithms=["HS256"],
                audience="case-access",
            )
            case = one(conn, "SELECT * FROM review_cases WHERE id=%s AND status='ESCALATED'", (grant["case_id"],))
            permitted = bool(
                case
                and grant["sub"] == str(user["id"])
                and grant["student_id"] == str(student["id"])
                and grant["version"] == case["version_no"]
            )
        except (jwt.InvalidTokenError, KeyError):
            permitted = False
    if not permitted:
        fail("NOT_FOUND", 404)
    return student


def reason(value):
    text = (value or "").strip()
    if not 10 <= len(text) <= 1000:
        fail("REASON_REQUIRED")
    return text
