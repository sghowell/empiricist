from p8.tensor import derive


def test_tensor_action_normalization():
    assert set(derive()["residuals"].values()) == {0}
