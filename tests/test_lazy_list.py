import copy

import pytest

from pyiceberg.lazy import LazyList


@pytest.fixture
def original() -> list[int]:
    return [1, 2, 3]


@pytest.fixture
def base(original: list[int]) -> list[int]:
    return copy.deepcopy(original)


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        (["1", "2", "3"], ["1", "3"]),
        (["1", "2", "3", "2"], ["1", "3", "2"]),
        (["2", "3", "2", "4"], ["3", "2", "4"]),
    ],
)
def test_lazy_list_remove(original: list[str], base: list[str], expected: list[str]):
    l = LazyList(base)
    l.remove("2")
    assert list(l) == expected
    assert base == original


def test_lazy_list_append(original: list[int], base: list[int]):
    l = LazyList(base)
    l.append(4)
    assert list(l) == [1, 2, 3, 4]
    assert base == original


def test_lazy_list_set(original: list[int], base: list[int]):
    l = LazyList(base)
    l[1] = 4
    assert list(l) == [1, 4, 3]
    assert base == original


def test_lazy_list_del(original: list[int], base: list[int]):
    l = LazyList(base)
    del l[1]
    assert list(l) == [1, 3]
    assert base == original


def test_lazy_list_insert(original: list[int], base: list[int]):
    l = LazyList(base)
    l.insert(1, 4)
    assert list(l) == [1, 4, 2, 3]
    assert base == original
