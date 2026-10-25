import pytest
from fastapi import HTTPException
from app.modules.career.catalogue import resolve_role, CATALOGUE
from app.modules.career.service import career


@pytest.mark.parametrize(
    "question,role",
    [
        ("How do I become a Data Scientist?", "DATA_SCIENTIST"),
        ("I want full-stack work", "FULL_STACK_DEVELOPER"),
        ("Prepare me for machine learning engineer", "ML_ENGINEER"),
        ("Cloud engineer skills", "CLOUD_ENGINEER"),
    ],
)
def test_role_aliases(question, role):
    assert resolve_role(question) == role


@pytest.mark.parametrize(
    "question,explicit",
    [
        ("data science or cloud engineer", None),
        ("an unknown job", None),
        ("data scientist", "UNSUPPORTED_ROLE"),
    ],
)
def test_ambiguous_unknown_or_invalid_explicit_roles_are_not_guessed(question, explicit):
    with pytest.raises(HTTPException) as caught:
        resolve_role(question, explicit)
    assert caught.value.detail["code"] == "UNKNOWN_CAREER_ROLE"
    assert {field["code"] for field in caught.value.detail["fields"]} == set(CATALOGUE)


def test_valid_explicit_role_overrides_ambiguous_question():
    assert resolve_role("data science or cloud engineer", "CLOUD_ENGINEER") == "CLOUD_ENGINEER"


def test_missing_skill_plan_has_study_project_and_deployment_phases():
    result = career(
        "DATA_SCIENTIST", {code: [] for code in ["PYTHON", "SQL", "STATISTICS", "PANDAS", "DATA_VISUALIZATION"]}
    )
    assert result["readiness_percent"] == 74
    assert [step["estimated_weeks"] for step in result["recommended_steps"]] == [2, 3, 1, 2, 3, 1]
    assert [step["priority"] for step in result["recommended_steps"]] == list(range(1, 7))
