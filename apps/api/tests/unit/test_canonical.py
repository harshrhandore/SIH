import pytest
from app.modules.audit.canonical import canonical


def test_canonical():
    assert canonical({"z": "e\u0301", "a": None}) == '{"a":null,"z":"é"}'
    with pytest.raises(ValueError):
        canonical({"bad": 1.5})
