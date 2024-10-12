"""CrossSections for KFactory."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from . import kdb
from .enclosure import DLayerEnclosure, LayerEnclosure

if TYPE_CHECKING:
    from .kcell import KCLayout


class SymmetricalCrossSection(BaseModel, frozen=True):
    """CrossSection which is symmetrical to its main_layer/width."""

    width: int
    enclosure: LayerEnclosure
    name: str

    def __init__(
        self, width: int, enclosure: LayerEnclosure, name: str | None = None
    ) -> None:
        """Initialized the CrossSection."""
        super().__init__(
            width=width, enclosure=enclosure, name=name or f"{enclosure.name}_{width}"
        )

    @model_validator(mode="after")
    def _validate_enclosure_main_layer(self) -> Self:
        if self.enclosure.main_layer is None:
            raise ValueError("Enclosures of cross sections must have a main layer.")
        if (self.width // 2) * 2 != self.width:
            raise ValueError(
                "Width of symmetrical cross sections must have be a multiple of 2. "
                "This could cause cross sections and extrusions to become unsymmetrical"
                " otherwise."
            )
        return self

    @cached_property
    def main_layer(self) -> kdb.LayerInfo:
        """Main Layer of the enclosure and cross section."""
        return self.enclosure.main_layer  # type: ignore[return-value]

    def to_dtype(self, kcl: KCLayout) -> DSymmetricalCrossSection:
        """Convert to a um based CrossSection."""
        return DSymmetricalCrossSection(
            width=kcl.to_um(self.width),
            enclosure=self.enclosure.to_dtype(kcl),
            name=self.name,
        )


class DSymmetricalCrossSection(BaseModel):
    """um based CrossSection."""

    width: float
    enclosure: DLayerEnclosure
    name: str | None = None

    def to_itype(self, kcl: KCLayout) -> SymmetricalCrossSection:
        """Convert to a dbu based CrossSection."""
        return SymmetricalCrossSection(
            width=kcl.to_dbu(self.width),
            enclosure=kcl.get_enclosure(self.enclosure.to_itype(kcl)),
            name=self.name,
        )
