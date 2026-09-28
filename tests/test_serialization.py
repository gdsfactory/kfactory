from typing import Any

import kfactory as kf
from kfactory.serialization import (
    DecoratorDict,
    DecoratorList,
    DecoratorTuple,
    hashable_to_original,
    to_hashable,
)


def test_hashable_roundtrip() -> None:
    d = {"b": [[1, {"c": [2]}], (3, 4)], "a": 1}
    hd = to_hashable(d)

    assert isinstance(hd, DecoratorDict)
    assert isinstance(hd["b"], DecoratorList)
    assert hash(hd) == hash(to_hashable({"a": 1, "b": [[1, {"c": [2]}], (3, 4)]}))
    assert hashable_to_original(hd) == d


def test_hashable_tuple() -> None:
    t = ((1.0, 2.0), (3.0, 4.0))
    assert to_hashable(t) is t

    d = {"a": ([1, 2], {"b": [3]}), "c": [(4, [5])]}
    hd = to_hashable(d)

    assert isinstance(hd["a"], DecoratorTuple)
    assert isinstance(hd["a"][0], DecoratorList)
    assert isinstance(hd["c"][0], DecoratorTuple)
    assert hash(hd) == hash(to_hashable({"c": [(4, [5])], "a": ([1, 2], {"b": [3]})}))

    original = hashable_to_original(hd)
    assert original == d
    assert type(original["a"]) is tuple
    assert type(original["a"][0]) is list
    assert type(original["c"][0]) is tuple


def test_cell_tuple_of_lists() -> None:
    kcl = kf.KCLayout("test_cell_tuple_of_lists")
    received: list[Any] = []

    @kcl.cell
    def c(x: tuple[list[int], ...]) -> kf.KCell:
        received.append(x)
        return kcl.kcell()

    c1 = c(x=([1, 2], [3]))
    assert c(x=([1, 2], [3])) is c1
    assert c(x=([1, 2], [4])) is not c1
    assert received == [([1, 2], [3]), ([1, 2], [4])]
    assert type(received[0]) is tuple
    assert type(received[0][0]) is list
