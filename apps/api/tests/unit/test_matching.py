from app.core.algorithms import clean
from app.modules.verification.matching import normalized_name, name_match, possible_match


def test_normalization_and_subset():
    assert clean("N/A") is None
    assert clean("0") == "0"
    assert normalized_name(" Dr. Riya  Sharma ") == "riya sharma"
    assert name_match("Riya", "Riya Sharma") == (100.0, False)
    assert name_match("Riya Sharma", "Sharma Riya")[1]


def test_corroboration():
    assert not possible_match(dict(full_name="Riya Sharma"), dict(full_name="Riya Sharma"))[1]
    assert possible_match(
        dict(full_name="Riya Sharma", dob="2004-06-15"), dict(full_name="Riya Sharma", dob="2004-06-15")
    )[1]
