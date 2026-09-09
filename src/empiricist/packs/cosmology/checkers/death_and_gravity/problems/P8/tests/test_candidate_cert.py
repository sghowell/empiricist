import pytest
from p8 import candidate_cert


@pytest.mark.parametrize("label", ("C", "D", "CD_matter"))
def test_all_time_sign_domain_and_tail_certificates(label):
    certificate = candidate_cert.build(label)
    assert certificate["candidate"] == label
    assert certificate["tail_certificates"]
    assert certificate["sign_certificates"]["Hamiltonian_J"]["numerator"]["roots"] == 0
