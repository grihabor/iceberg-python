from __future__ import annotations

from collections.abc import ItemsView, MutableMapping
from typing import Any, Final, Iterator, Mapping, Sequence, TypeVar, overload

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
        # sorted list of removed indices
        self._removed_indices: list[int] = []

    def __getitem__(self, i: int, /) -> _T:
        if i < 0:
            raise NotImplementedError

        offset = 0
        for r in self._removed_indices:
            if r < i:
                offset += 1
                continue
            if r == i:
                raise IndexError(i)
            break

        return self._base[i - offset]

    def __iter__(self) -> Iterator[_T]:
        r = 0
        for i, value in enumerate(self._base):
            if r < len(self._removed_indices) and i == self._removed_indices[r]:
                r += 1
                continue
            yield value

    def __len__(self) -> int:
        return len(self._base) - len(self._removed_indices)

    def remove(self, v: _T, /) -> None:
        for i, value in enumerate(self):
            if value == v:
                self._removed_indices.append(i)
        self._removed_indices.sort()


@overload
def make_lazy(obj: Mapping[_KT, _VT], /) -> LazyDict[_KT, _VT]:
    pass


@overload
def make_lazy(obj: Sequence[_VT], /) -> LazyList[_VT]:
    pass


def make_lazy(obj: Any, /) -> Any:
    pass
