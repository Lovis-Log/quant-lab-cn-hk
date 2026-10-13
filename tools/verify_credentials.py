"""Test the real Windows vault using a disposable, isolated dummy credential."""

import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quant_lab.credentials import remember_key, load_key, clear_key

target = "QuantLabCNHK/Validation/" + uuid4().hex
dummy = "sk-validation-" + uuid4().hex
try:
    remember_key(dummy, target=target)
    assert load_key(target=target) == dummy
finally:
    clear_key(target=target)
assert load_key(target=target) is None
print(json.dumps({"windows_vault_roundtrip": True, "isolated_dummy_removed": True}))
