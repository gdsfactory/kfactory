"""CrossSections for KFactory."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict, cast

from pydantic import BaseModel, Field, model_validator

from . import kdb
from .enclosure import DLayerEnclosure, LayerEnclosure, LayerEnclosureSpec

if TYPE_CHECKING:
    from .layout import KCLayout


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


class CrossSectionSpec(TypedDict):
    name: NotRequired[str]
    sections: NotRequired[
        list[tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]]
    ]
    main_layer: kdb.LayerInfo
    width: int | float
    dsections: NotRequired[
        list[tuple[kdb.LayerInfo, float] | tuple[kdb.LayerInfo, float, float]]
    ]


class CrossSectionModel(BaseModel):
    cross_sections: dict[str, SymmetricalCrossSection] = Field(default_factory=dict)
    kcl: KCLayout

    def get_cross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpec
        | DSymmetricalCrossSection,
    ) -> SymmetricalCrossSection:
        if isinstance(
            cross_section, SymmetricalCrossSection
        ) and cross_section.enclosure != self.kcl.get_enclosure(
            cross_section.enclosure
        ):
            return self.get_cross_section(
                CrossSectionSpec(
                    sections=cross_section.enclosure.model_dump()["sections"],
                    main_layer=cross_section.main_layer,
                    name=cross_section.name,
                    width=cross_section.width,
                )
            )

        if isinstance(cross_section, str):
            return self.cross_sections[cross_section]
        elif isinstance(cross_section, DSymmetricalCrossSection):
            cross_section = cross_section.to_itype(self.kcl)
        elif isinstance(cross_section, dict):
            cast(CrossSectionSpec, cross_section)
            if "dsections" in cross_section:
                cross_section = SymmetricalCrossSection(
                    width=self.kcl.to_dbu(cross_section["width"]),
                    enclosure=self.kcl.layer_enclosures.get_enclosure(
                        enclosure=LayerEnclosureSpec(
                            dsections=cross_section["dsections"],
                            main_layer=cross_section["main_layer"],
                        ),
                        kcl=self.kcl,
                    ),
                    name=cross_section.get("name", None),
                )
            else:
                w = cross_section["width"]
                if not isinstance(w, int) and not w.is_integer():
                    raise ValueError(
                        "A CrossSectionSpec with 'sections' must have a width in dbu."
                    )
                cross_section = SymmetricalCrossSection(
                    width=int(w),
                    enclosure=self.kcl.layer_enclosures.get_enclosure(
                        LayerEnclosureSpec(
                            sections=cross_section.get("sections", []),
                            main_layer=cross_section["main_layer"],
                        ),
                        kcl=self.kcl,
                    ),
                    name=cross_section.get("name", None),
                )
        if cross_section.name not in self.cross_sections:
            self.cross_sections[cross_section.name] = cross_section
            return cross_section
        return self.cross_sections[cross_section.name]

    def __repr__(self) -> str:
        return repr(self.cross_sections)


SymmetricalCrossSection.model_rebuild()
