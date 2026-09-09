import json

import pytest
from p8.verify import CERTIFICATE, check_certificate


def test_stored_certificate_replays():
    report = check_certificate()
    assert report["claim"] == "P8-0"
    assert report["not_established"]


def test_modified_certificate_is_rejected(tmp_path):
    data = json.loads(CERTIFICATE.read_text())
    data["horndeski"]["FS"] = "0"
    changed = tmp_path / "tampered.json"
    changed.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        check_certificate(changed)
