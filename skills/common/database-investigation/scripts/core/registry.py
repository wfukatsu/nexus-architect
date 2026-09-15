"""Only repository-maintained adapters can supply code or SQL."""
import importlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def load_adapter(product, root=ROOT):
    registry = json.loads((root / "adapters/registry.json").read_text())
    if product not in registry:
        raise ValueError("unregistered database product")
    folder = registry[product]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", folder):
        raise ValueError("invalid registered adapter name")
    spec = json.loads((root / "adapters" / folder / "adapter.json").read_text())
    if spec["id"] != product:
        raise ValueError("registry identity mismatch")
    module = importlib.import_module("adapters." + folder)
    return spec, module
