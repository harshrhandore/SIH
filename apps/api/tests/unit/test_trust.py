from app.modules.trust.service import trust


def test_current_approval_and_high_risk_trust_components():
    inputs = dict(complete_fields=10, certificates=2, approved=True)
    assert trust(inputs)["score"] == 91
    assert trust({**inputs, "risk": 83})["score"] == 76
