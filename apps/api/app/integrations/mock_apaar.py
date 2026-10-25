from datetime import datetime, timezone
from typing import Protocol, Mapping, Any
from app.core.algorithms import valid_id


class ExternalVerificationAdapter(Protocol):
    def verify(self, student_snapshot: Mapping[str, Any]) -> dict: ...


class MockApaarAdapter:
    def verify(self, student_snapshot):
        identifier = student_snapshot.get("apaar_id")
        if not valid_id(identifier) or student_snapshot.get("data_quality_status") != "PASSED_LOCAL_CHECKS":
            raise ValueError("LOCAL_CHECKS_REQUIRED")
        status = "MOCK_NO_MATCH" if int(identifier[4:-1]) % 10 == 0 else "MOCK_MATCH"
        return dict(
            adapter="MockApaarAdapter",
            status=status,
            official=False,
            label="MOCK, not official",
            checked_at=datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            reasons=[
                "Synthetic identifier passed deterministic mock lookup."
                if status == "MOCK_MATCH"
                else "Synthetic counter selected the deterministic mock no-match path."
            ],
            reference="synthetic:" + identifier,
        )
