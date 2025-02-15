import copy
import itertools
import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterator, MutableMapping

import pytest

from pyiceberg.lazy import LazyDict


class OpName(StrEnum):
    SET = "set"
    DEL = "del"
    GET = "get"


@dataclass(frozen=True)
class Op:
    name: OpName
    key: int
    value: int


@pytest.fixture
def number_of_ops() -> int:
    return


@pytest.fixture
def ops_stream() -> Iterator[Op]:
    r = random.Random()
    names = list(OpName.__members__.values())
    return itertools.starmap(
        Op,
        zip(
            (r.choice(names) for _ in itertools.count()),
            (r.randint(0, 10) for _ in itertools.count()),
            (r.randint(10, 100) for _ in itertools.count()),
        ),
    )


@pytest.fixture
def min_ops_in_batch() -> int:
    return 0


@pytest.fixture
def max_ops_in_batch() -> int:
    return 1000


@pytest.fixture
def ops_batch_stream(ops_stream: Iterator[Op], min_ops_in_batch: int, max_ops_in_batch: int) -> Iterator[Iterator[Op]]:
    return (list(itertools.islice(ops_stream, random.randint(min_ops_in_batch, max_ops_in_batch))) for _ in itertools.count())


@pytest.fixture
def max_batches() -> int:
    return 1000


@pytest.fixture
def ops_batches(ops_batch_stream: Iterator[Iterator[Op]], max_batches: int) -> Iterator[Iterator[Op]]:
    return list(itertools.islice(ops_batch_stream, random.randint(0, max_batches)))


def test_dict(ops_batches: Iterator[Iterator[Op]]):
    control = {}
    original = {}

    for batch in ops_batches:
        # original is now the new base
        base = copy.deepcopy(original)
        lazy = LazyDict(base)
        for op in batch:
            control_result = run_op(op, control)
            lazy_result = run_op(op, lazy)
            assert control_result == lazy_result

        # make sure base didn't change
        assert original == base
        # make sure lazy dict items match the control
        original = dict(lazy.items())
        assert original == control


@dataclass(frozen=True)
class _KeyError:
    value: int


def run_op(op: Op, d: MutableMapping[int, int]) -> int | None | _KeyError:
    try:
        match op.name:
            case OpName.GET:
                return d[op.key]
            case OpName.SET:
                d[op.key] = op.value
            case OpName.DEL:
                del d[op.key]

    except KeyError as e:
        (value,) = e.args
        return _KeyError(value)
