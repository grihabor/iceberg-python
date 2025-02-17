from __future__ import annotations

import itertools
from bisect import bisect_left
from collections.abc import ItemsView, MutableMapping
from typing import Any, Final, Iterator, Mapping, MutableSequence, Sequence, TypeVar, overload, override

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


_REMOVED: Final = object()
_MISSING: Final = object()


class _LazyItemsView(ItemsView[_KT, _VT]):
    def __init__(self, base: Mapping[_KT, Any], diff: Mapping[_KT, Any], /) -> None:
        self._base = base
        self._diff = diff

    def __iter__(self) -> Iterator[tuple[_KT, _VT]]:
        for k, original in self._base.items():
            updated = self._diff.get(k, _MISSING)
            if updated is _MISSING:
                yield k, original
                continue
            if updated is _REMOVED:
                continue
            yield k, updated

        for k, updated in self._diff.items():
            if updated is _REMOVED:
                continue
            if k in self._base:
                # we've already yielded it
                continue
            yield k, updated


class LazyDict(MutableMapping[_KT, _VT]):
    def __init__(self, m: Mapping[_KT, _VT], /) -> None:
        self._base = m
        # The real type signature is dict[_KT, _VT | Literal[_REMOVED]], but
        # mypy doesn't support literals for sentinels, see
        # https://github.com/python/typing/issues/689
        self._diff: dict[_KT, Any] = {}

    def __setitem__(self, key: _KT, value: _VT, /) -> None:
        self._diff[key] = value

    def __getitem__(self, key: _KT, /) -> _VT:
        value = self._diff.get(key, _MISSING)
        if value is _MISSING:
            return self._base[key]
        if value is _REMOVED:
            raise KeyError(key)
        return value

    def __delitem__(self, key: _KT, /) -> None:
        value = self._diff.get(key, _MISSING)
        if value is _MISSING and key not in self._base:
            raise KeyError(key)
        if value is _REMOVED:
            raise KeyError(key)
        self._diff[key] = _REMOVED

    def items(self) -> ItemsView[_KT, _VT]:
        return _LazyItemsView(self._base, self._diff)

    def __iter__(self) -> Iterator[_KT]:
        return (k for k, _ in self.items())

    def __len__(self) -> int:
        return sum(1 for _ in self.items())


_T = TypeVar("_T")


class LazyList(MutableSequence[_T]):
    def __init__(self, s: MutableSequence[_T], /) -> None:
        self._base = s
        # Sorted list of removed base indices.
        self._removes: list[int] = []
        # Mapping from base indices to updated values.
        self._updates: dict[int, _T] = {}
        # Pairs (index, inserted_value) sorted by index. Indices can repeat.
        self._inserts: list[tuple[int, _T]] = []

    def __getitem__(self, i: int, /) -> _T:
        if i < 0:
            raise NotImplementedError

        offset = 0
        for r in self._removes:
            if r < i:
                offset += 1
                continue
            if r == i:
                raise IndexError(i)
            break

        return self._base[i - offset]

    def __setitem__(self, index: int, value: _T) -> None:
        if index < 0:
            raise NotImplementedError

        removed_index = next((i for i, r in enumerate(self._removes) if r == index), None)
        if removed_index is not None:
            del self._removes[removed_index]
        self._updates[index] = value

    def __delitem__(self, index: int) -> None:
        if index < 0:
            raise NotImplementedError

        r, offset = 0, None
        while offset != 0:
            offset = bisect_left(self._removes[r:], index)
            index, r = index + offset, r + offset

        if r == len(self._removes):
            self._removes.append(index)
            return

        if self._removes[r] == index:
            raise KeyError(index)

        self._removes.insert(r, index)

    def __iter__(self) -> Iterator[_T]:
        rem, ins = 0, 0
        # Hacky chain call helps to handle inserts at the end of the base list.
        for i, value in enumerate(itertools.chain(self._base, ())):
            while ins < len(self._inserts) and i == (pair := self._inserts[ins])[0]:
                yield pair[1]
                ins += 1

            print(f"{ins=}")
            if i == len(self._base):
                return

            if rem < len(self._removes) and i == self._removes[rem]:
                rem += 1
                continue
            if (updated := self._updates.get(i, _MISSING)) is not _MISSING:
                yield updated
                continue
            yield value

    def __len__(self) -> int:
        return len(self._base) - len(self._removes)

    def append(self, v: _T, /) -> None:
        self._inserts.append((len(self._base), v))

    def insert(self, index: int, value: _T) -> None:
        raise NotImplementedError

    @override
    def remove(self, v: _T, /) -> None:
        """Remove the first item from the list whose value is equal to x. It raises a ValueError if there is no such item."""
        for i, value in enumerate(self):
            if value == v:
                del self[i]
                return


@overload
def make_lazy(obj: Mapping[_KT, _VT], /) -> LazyDict[_KT, _VT]:
    pass


@overload
def make_lazy(obj: Sequence[_VT], /) -> LazyList[_VT]:
    pass


def make_lazy(obj: Any, /) -> Any:
    pass
