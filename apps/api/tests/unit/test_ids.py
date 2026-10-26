from app.core.identifiers import synthetic_id, valid_id


def test_id_boundaries():
    assert synthetic_id(1) == "SYN-0000000000018"
    for counter in [1, 2, 9, 10, 100001]:
        assert valid_id(synthetic_id(counter))
        assert not valid_id(synthetic_id(counter)[:-1] + "x")
    assert not valid_id("SYN-000000 000018")
