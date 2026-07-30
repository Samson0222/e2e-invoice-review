"""Generic, typed pipeline steps that chain together with `.then()`."""

from abc import ABC, abstractmethod


class Step[TIn, TOut](ABC):
    """A single pipeline stage. Compose stages with `.then()` to build a larger `Step`."""

    @abstractmethod
    def run(self, value: TIn) -> TOut: ...

    def then[TNext](self, next_step: "Step[TOut, TNext]") -> "Step[TIn, TNext]":
        return _ChainedStep(self, next_step)


class _ChainedStep[TIn, TOut, TNext](Step[TIn, TNext]):
    def __init__(self, first: Step[TIn, TOut], second: Step[TOut, TNext]) -> None:
        self._first = first
        self._second = second

    def run(self, value: TIn) -> TNext:
        return self._second.run(self._first.run(value))
