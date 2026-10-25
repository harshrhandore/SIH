"""Version-one immutable local role weight catalogue."""

import json
from app.settings import ROOT

CATALOGUE: dict[str, dict[str, int]] = json.loads((ROOT / "db/seed/catalogue.json").read_text(encoding="utf-8"))

ALIASES = {
    "DATA_SCIENTIST": ["data scientist", "data science"],
    "FULL_STACK_DEVELOPER": ["full stack", "full-stack", "web developer"],
    "ML_ENGINEER": ["ml engineer", "machine learning engineer"],
    "CLOUD_ENGINEER": ["cloud engineer"],
}


def resolve_role(question, explicit_role=None):
    from app.core.errors import fail

    matches = {code for code, aliases in ALIASES.items() if any(alias in question.casefold() for alias in aliases)}
    selected = explicit_role if explicit_role is not None else next(iter(matches)) if len(matches) == 1 else None
    if selected not in CATALOGUE:
        fail(
            "UNKNOWN_CAREER_ROLE",
            422,
            "Choose one supported role: " + ", ".join(CATALOGUE),
            fields=[dict(field="role_code", code=code, message=code.replace("_", " ").title()) for code in CATALOGUE],
        )
    return selected
