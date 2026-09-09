from p8.exclusions import algebra, rows


def test_exclusion_identities():
    assert set(algebra()["residuals"].values()) == {0}


def test_ladder_and_minimal_sets():
    table = rows()
    assert len(table) == 16
    for sector, expected_count, expected_minimal in (("M0", 12, {"C", "D"}), ("M1", 4, {"CD"})):
        exists = [r["groups"] for r in table if r[sector] == "E"]
        assert len(exists) == expected_count
        minimal = {r for r in exists if not any(set(s) < set(r) for s in exists)}
        assert minimal == expected_minimal
        for lower in exists:
            assert all(r[sector] == "E" for r in table if set(lower) <= set(r["groups"]))
