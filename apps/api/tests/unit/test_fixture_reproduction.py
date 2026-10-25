from tempfile import TemporaryDirectory
from pathlib import Path
from app.settings import ROOT
from db.seed.fixtures import generate


def test_all_fixture_bytes_reproduce():
    base = ROOT / ".local"
    base.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=base, prefix="fixture-repro-") as temporary:
        path = Path(temporary).resolve()
        assert path.is_relative_to(ROOT.resolve())
        first = generate(path / "first")
        second = generate(path / "second")
        assert first["hashes"] == second["hashes"]
