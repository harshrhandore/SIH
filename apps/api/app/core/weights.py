from functools import lru_cache
import yaml
from app.settings import ROOT


@lru_cache(maxsize=2)
def load_weights(name):
    if name not in {"fraud", "trust"}:
        raise ValueError("Unknown fixed weight catalogue")
    return yaml.safe_load((ROOT / "apps/api/app/config" / f"{name}_weights.yaml").read_text())
