import pytest

from kfactory.serialization import check_metadata_type, convert_metadata_type


def test_convert_metadata_type() -> None:
    assert convert_metadata_type(42) == 42
    assert convert_metadata_type(3.14) == 3.14
    assert convert_metadata_type("test") == "test"
    assert convert_metadata_type(True) is True
    assert convert_metadata_type(None) is None
    assert convert_metadata_type((1, 2, 3)) == (1, 2, 3)
    assert convert_metadata_type([1, 2, 3]) == [1, 2, 3]
    assert convert_metadata_type({"key": "value"}) == {"key": "value"}


def test_check_metadata_type() -> None:
    assert check_metadata_type(42) == 42
    assert check_metadata_type(3.14) == 3.14
    assert check_metadata_type("test") == "test"
    assert check_metadata_type(True) is True
    assert check_metadata_type(None) is None
    assert check_metadata_type((1, 2, 3)) == (1, 2, 3)
    assert check_metadata_type([1, 2, 3]) == [1, 2, 3]
    assert check_metadata_type({"key": "value"}) == {"key": "value"}

    with pytest.raises(ValueError):
        check_metadata_type(set([1, 2, 3]))  # type: ignore
