"""Deterministic readiness from scoped, evidenced skills."""

from typing import Any
from app.modules.career.catalogue import CATALOGUE
from uuid import uuid4
from app.core.http import idem, listing, pagination
from app.core.security import allow, student_scope
from app.core.rate_limit import limit
from app.db.session import connect
from app.modules.career.catalogue import resolve_role
from app.modules.career import repository


def ask(student_id, body, request, user):
    allow(user, "STUDENT")
    limit(("career", str(user["id"])), 20)
    role = resolve_role(body.question, body.role_code)
    with connect() as conn:
        student_scope(conn, user, student_id, request)

        def work(key):
            result = career(role, repository.evidenced_skills(conn, student_id))
            sid = uuid4()
            repository.save_session(conn, sid, student_id, body.question, role, result)
            return {**result, "session_id": sid}

        return idem(conn, user, request, body.model_dump(), work)


def history(student_id, request, page, page_size, user):
    allow(user, "STUDENT", "OPERATOR", "OFFICER")
    offset = pagination(page, page_size)
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        rows, total = repository.history(conn, student_id, page_size, offset)
    return listing(rows, total, page, page_size)


def career(role, skills):
    weights = CATALOGUE[role]
    matched: list[dict[str, Any]] = [
        {"code": k, "label": k.replace("_", " ").title(), "weight": w, "evidence": skills[k]}
        for k, w in weights.items()
        if k in skills
    ]
    missing_inputs: list[dict[str, Any]] = [
        {"code": k, "label": k.replace("_", " ").title(), "weight": w} for k, w in weights.items() if k not in skills
    ]
    missing = sorted(missing_inputs, key=lambda x: (-x["weight"], x["code"]))
    score = sum(s["weight"] for s in matched)
    return dict(
        role_code=role,
        readiness_percent=score,
        matched_skills=matched,
        missing_skills=missing,
        recommended_steps=[
            dict(
                priority=i * 3 + step + 1,
                action=template.format(skill=s["label"]),
                estimated_weeks=weeks,
                reason=f"{s['label']} contributes {s['weight']} missing points.",
            )
            for i, s in enumerate(missing)
            for step, (template, weeks) in enumerate(
                [
                    ("Study the foundations of {skill} with small practice exercises.", 2),
                    ("Build and measure a project demonstrating {skill}.", 3),
                    ("Deploy and document the {skill} project and its results.", 1),
                ]
            )
        ],
        suggested_courses=[
            dict(title=s["label"] + " Foundations", provider="Generic learning resource", url=None) for s in missing
        ],
        explanation=f"Your evidenced skills cover {score} of 100 role-weight points. Self-reported skills add no points.",
        phrasing_source="RULE_BASED",
        catalogue_version=1,
    )
