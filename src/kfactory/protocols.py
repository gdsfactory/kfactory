from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, overload, runtime_checkable

from .typings import KC, KCellParams, TUnit

if TYPE_CHECKING:
    from .layer import LayerEnum


class KCellFunc(Protocol[KCellParams, KC]):
    __name__: str

    def __call__(self, *args: KCellParams.args, **kwargs: KCellParams.kwargs) -> KC: ...


@runtime_checkable
class PointLike(Protocol[TUnit]):
    x: TUnit
    y: TUnit


@runtime_checkable
class BoxLike(Protocol[TUnit]):
    left: TUnit
    bottom: TUnit
    right: TUnit
    top: TUnit

    def center(self) -> PointLike[TUnit]: ...
    def width(self) -> TUnit: ...
    def height(self) -> TUnit: ...


@runtime_checkable
class BoxFunction(Protocol[TUnit]):
    @overload
    def __call__(self) -> BoxLike[TUnit]: ...
    @overload
    def __call__(self, layer: LayerEnum | int) -> BoxLike[TUnit]: ...
    def __call__(self, layer: LayerEnum | int | None = None) -> BoxLike[TUnit]: ...
