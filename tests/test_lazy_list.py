from pyiceberg.lazy import LazyList


def test_lazy_list():
    arr = [1, 2, 3]
    l = LazyList(arr)
    l.remove(2)
    assert list(l) == [1, 3]
