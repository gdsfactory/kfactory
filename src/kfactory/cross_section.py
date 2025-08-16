"""CrossSections for KFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NotRequired,
    Self,
    TypedDict,
    overload,
)

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from .enclosure import DLayerEnclosure, LayerEnclosure, LayerEnclosureSpec
from .typings import TUnit

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from . import kdb
    from .layout import KCLayout

__all__ = [
    "CrossSection",
    "CrossSectionSpec",
    "DCrossSection",
    "DCrossSectionSpec",
    "SymmetricalCrossSection",
]


class SymmetricalCrossSection(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """CrossSection which is symmetrical to its main_layer/width."""

    width: int
    enclosure: LayerEnclosure
    name: str = ""
    radius: int | None = None
    radius_min: int | None = None
    bbox_sections: dict[kdb.LayerInfo, int]

    def __init__(
        self,
        width: int,
        enclosure: LayerEnclosure,
        name: str | None = None,
        bbox_sections: dict[kdb.LayerInfo, int] | None = None,
        radius: int | None = None,
        radius_min: int | None = None,
    ) -> None:
        """Initialized the CrossSection."""
        super().__init__(
            width=width,
            enclosure=enclosure,
            name=name or f"{enclosure.name}_{width}",
            bbox_sections=bbox_sections or {},
            radius=radius,
            radius_min=radius_min,
        )

    @model_validator(mode="before")
    @classmethod
    def _set_name(cls, data: Any) -> Any:
        data["name"] = data.get("name") or f"{data['enclosure'].name}_{data['width']}"
        return data

    @model_validator(mode="after")
    def _validate_enclosure_main_layer(self) -> Self:
        if self.enclosure.main_layer is None:
            raise ValueError("Enclosures of cross sections must have a main layer.")
        if self.width % 2:
            raise ValueError(
                "Width of symmetrical cross sections must have be a multiple of 2 dbu. "
                "This could cause cross sections and extrusions to become unsymmetrical"
                " otherwise."
            )
        if not self.width:
            raise ValueError("Cross section with width 0 is not allowed.")
        return self

    @model_validator(mode="after")
    def _validate_width(self) -> Self:
        if self.width <= 0:
            raise ValueError("Width must be greater than 0.")
        return self

    @property
    def main_layer(self) -> kdb.LayerInfo:
        """Main Layer of the enclosure and cross section."""
        assert self.enclosure.main_layer is not None
        return self.enclosure.main_layer

    def to_dtype(self, kcl: KCLayout) -> DSymmetricalCrossSection:
        """Convert to a um based CrossSection."""
        return DSymmetricalCrossSection(
            width=kcl.to_um(self.width),
            enclosure=self.enclosure.to_dtype(kcl),
            name=self.name,
        )

    def get_xmax(self) -> int:
        return self.width // 2 + max(
            s.d_max
            for sections in self.enclosure.layer_sections.values()
            for s in sections.sections
        )

    def model_copy(
        self, *, update: Mapping[str, Any] | None = {"name": None}, deep: bool = False
    ) -> SymmetricalCrossSection:
        return super().model_copy(update=update, deep=deep)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, TCrossSection):
            return o == self
        return super().__eq__(o)


class DSymmetricalCrossSection(BaseModel):
    """um based CrossSection."""

    width: float
    enclosure: DLayerEnclosure
    name: str | None = None

    @model_validator(mode="after")
    def _validate_width(self) -> Self:
        if self.width <= 0:
            raise ValueError("Width must be greater than 0.")
        return self

    def to_itype(self, kcl: KCLayout) -> SymmetricalCrossSection:
        """Convert to a dbu based CrossSection."""
        return SymmetricalCrossSection(
            width=kcl.to_dbu(self.width),
            enclosure=kcl.get_enclosure(self.enclosure.to_itype(kcl)),
            name=self.name,
        )


class TCrossSection(ABC, Generic[TUnit]):
    _base: SymmetricalCrossSection = PrivateAttr()
    kcl: KCLayout

    @overload
    @abstractmethod
    def __init__(self, kcl: KCLayout, *, base: SymmetricalCrossSection) -> None: ...

    @overload
    @abstractmethod
    def __init__(
        self,
        kcl: KCLayout,
        width: TUnit,
        layer: kdb.LayerInfo,
        sections: Sequence[tuple[TUnit, TUnit] | tuple[TUnit]],
        radius: TUnit | None = None,
        radius_min: TUnit | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[TUnit] | None = None,
    ) -> None: ...

    @abstractmethod
    def __init__(
        self,
        kcl: KCLayout,
        width: TUnit | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: Sequence[tuple[TUnit, TUnit] | tuple[TUnit]] | None = None,
        radius: TUnit | None = None,
        radius_min: TUnit | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[TUnit] | None = None,
        base: SymmetricalCrossSection | None = None,
    ) -> None: ...

    @property
    def base(self) -> SymmetricalCrossSection:
        return self._base

    @property
    @abstractmethod
    def width(self) -> TUnit: ...

    @property
    def layer(self) -> kdb.LayerInfo:
        return self._base.main_layer

    @property
    def enclosure(self) -> LayerEnclosure:
        return self._base.enclosure

    @property
    def name(self) -> str:
        return self._base.name

    def to_itype(self) -> CrossSection:
        return CrossSection(kcl=self.kcl, base=self._base)

    def to_dtype(self) -> DCrossSection:
        return DCrossSection(kcl=self.kcl, base=self._base)

    @property
    @abstractmethod
    def sections(self) -> dict[kdb.LayerInfo, list[tuple[TUnit | None, TUnit]]]: ...

    @property
    @abstractmethod
    def radius(self) -> TUnit | None: ...

    @property
    @abstractmethod
    def radius_min(self) -> TUnit | None: ...

    @property
    @abstractmethod
    def bbox_sections(
        self,
    ) -> dict[kdb.LayerInfo, TUnit]: ...

    @abstractmethod
    def get_xmin_xmax(self) -> tuple[TUnit, TUnit]: ...

    @abstractmethod
    def model_copy(
        self, *, update: Mapping[str, Any] = {"name": None}, deep: bool
    ) -> Self: ...

    def __eq__(self, o: object) -> bool:
        if isinstance(o, TCrossSection):
            return self.base == o.base
        if isinstance(o, SymmetricalCrossSection):
            return self.base == o
        return False


class CrossSection(TCrossSection[int]):
    @overload
    def __init__(self, kcl: KCLayout, *, base: SymmetricalCrossSection) -> None: ...

    @overload
    def __init__(
        self,
        kcl: KCLayout,
        width: int,
        layer: kdb.LayerInfo,
        sections: Sequence[tuple[kdb.LayerInfo, int, int] | tuple[kdb.LayerInfo, int]],
        radius: int | None = None,
        radius_min: int | None = None,
        name: str | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[int] | None = None,
    ) -> None: ...

    def __init__(
        self,
        kcl: KCLayout,
        width: int | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: Sequence[tuple[kdb.LayerInfo, int, int] | tuple[kdb.LayerInfo, int]]
        | None = None,
        radius: int | None = None,
        radius_min: int | None = None,
        name: str | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[int] | None = None,
        base: SymmetricalCrossSection | None = None,
    ) -> None:
        if not base:
            if bbox_layers:
                if not bbox_offsets:
                    bbox_offsets = [0 for _ in range(len(bbox_layers))]
                elif len(bbox_offsets) != len(bbox_layers):
                    raise ValueError(
                        "Length of the bbox_layers list and the bbox_offsets list"
                        " must be the same "
                        f"{len(bbox_layers)=}, {len(bbox_offsets)=}"
                    )
            else:
                bbox_layers = []
                bbox_offsets = []
            if width is None or layer is None or sections is None:
                raise ValueError(
                    "If no base is given, width, layer, and sections must be defined"
                )
            base = kcl.get_symmetrical_cross_section(
                SymmetricalCrossSection(
                    width=width,
                    enclosure=LayerEnclosure(sections=sections, main_layer=layer),
                    name=name,
                    bbox_sections={
                        s[0]: s[1]
                        for s in zip(bbox_layers, bbox_offsets)  # noqa: B905
                    },
                    radius=radius,
                    radius_min=radius_min,
                )
            )
        self.kcl = kcl
        self._base = base

    @property
    def sections(self) -> dict[kdb.LayerInfo, list[tuple[int | None, int]]]:
        items = self._base.enclosure.layer_sections.items()
        return {
            layer: [(section.d_min, section.d_max) for section in sections.sections]
            for layer, sections in items
        }

    @property
    def bbox_sections(self) -> dict[kdb.LayerInfo, int]:
        return self._base.bbox_sections.copy()

    @property
    def width(self) -> int:
        return self._base.width

    @property
    def radius(self) -> int | None:
        return self._base.radius

    @property
    def radius_min(self) -> int | None:
        return self._base.radius_min

    def get_xmin_xmax(self) -> tuple[int, int]:
        xmax = self._base.get_xmax()
        return (xmax, xmax)

    def model_copy(
        self, *, update: Mapping[str, Any] = {"name": None}, deep: bool
    ) -> CrossSection:
        return CrossSection(
            kcl=self.kcl, base=self.base.model_copy(update=update, deep=deep)
        )


class DCrossSection(TCrossSection[float]):
    @overload
    def __init__(self, kcl: KCLayout, *, base: SymmetricalCrossSection) -> None: ...

    @overload
    def __init__(
        self,
        kcl: KCLayout,
        width: float,
        layer: kdb.LayerInfo,
        sections: list[
            tuple[kdb.LayerInfo, float, float] | tuple[kdb.LayerInfo, float]
        ],
        radius: float | None = None,
        radius_min: float | None = None,
        name: str | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[float] | None = None,
    ) -> None: ...

    def __init__(
        self,
        kcl: KCLayout,
        width: float | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: list[tuple[kdb.LayerInfo, float, float] | tuple[kdb.LayerInfo, float]]
        | None = None,
        radius: float | None = None,
        radius_min: float | None = None,
        name: str | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[float] | None = None,
        base: SymmetricalCrossSection | None = None,
    ) -> None:
        if not base:
            if bbox_layers:
                if not bbox_offsets:
                    bbox_offsets = [0 for _ in range(len(bbox_layers))]
                elif len(bbox_offsets) != len(bbox_layers):
                    raise ValueError(
                        "Length of the bbox_layers list and the bbox_offsets list"
                        " must be the same "
                        f"{len(bbox_layers)=}, {len(bbox_offsets)=}"
                    )
            else:
                bbox_layers = []
                bbox_offsets = []
            if width is None or layer is None or sections is None:
                raise ValueError(
                    "If no base is given, width, layer, and sections must be defined"
                )
            base = kcl.get_symmetrical_cross_section(
                SymmetricalCrossSection(
                    width=kcl.to_dbu(width),
                    enclosure=LayerEnclosure(
                        sections=[
                            (s[0], *[kcl.to_dbu(s[i]) for i in range(1, len(s))])  # type: ignore[misc, arg-type]
                            for s in sections
                        ],
                        main_layer=layer,
                    ),
                    name=name,
                    bbox_sections={
                        s[0]: kcl.to_dbu(s[1])
                        for s in zip(bbox_layers, bbox_offsets)  # noqa: B905
                    },
                    radius=kcl.to_dbu(radius) if radius else None,
                    radius_min=kcl.to_dbu(radius_min) if radius_min else None,
                )
            )
        self.kcl = kcl
        self._base = base

    @property
    def sections(self) -> dict[kdb.LayerInfo, list[tuple[float | None, float]]]:
        items = self._base.enclosure.layer_sections.items()
        return {
            layer: [
                (
                    self.kcl.to_um(section.d_min)
                    if section.d_min is not None
                    else None,
                    self.kcl.to_um(section.d_max),
                )
                for section in sections.sections
            ]
            for layer, sections in items
        }

    @property
    def bbox_sections(self) -> dict[kdb.LayerInfo, float]:
        return {k: self.kcl.to_um(v) for k, v in self._base.bbox_sections.items()}

    @property
    def width(self) -> float:
        return self.kcl.to_um(self._base.width)

    @property
    def radius(self) -> float | None:
        return self.kcl.to_um(self._base.radius)

    @property
    def radius_min(self) -> float | None:
        return self.kcl.to_um(self._base.radius_min)

    def get_xmin_xmax(self) -> tuple[float, float]:
        xmax = self.kcl.to_um(self._base.get_xmax())
        return (xmax, xmax)

    def model_copy(
        self, *, update: Mapping[str, Any] = {"name": None}, deep: bool
    ) -> DCrossSection:
        return DCrossSection(
            kcl=self.kcl, base=self.base.model_copy(update=update, deep=deep)
        )


class TCrossSectionSpec(TypedDict, Generic[TUnit]):
    name: NotRequired[str]
    sections: NotRequired[
        list[tuple[kdb.LayerInfo, TUnit] | tuple[kdb.LayerInfo, TUnit, TUnit]]
    ]
    layer: kdb.LayerInfo
    width: TUnit
    bbox_layers: NotRequired[Sequence[kdb.LayerInfo]]
    bbox_offsets: NotRequired[Sequence[TUnit]]


class CrossSectionSpec(TCrossSectionSpec[int]):
    unit: NotRequired[Literal["dbu"]]


class DCrossSectionSpec(TCrossSectionSpec[float]):
    unit: Literal["um"]


class CrossSectionModel(BaseModel):
    cross_sections: dict[str, SymmetricalCrossSection] = Field(default_factory=dict)
    kcl: KCLayout

    def __getitem__(self, name: str) -> SymmetricalCrossSection:
        return self.cross_sections[name]

    def get_cross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | DSymmetricalCrossSection
        | CrossSectionSpec
        | DCrossSectionSpec
        | CrossSection
        | DCrossSection,
    ) -> SymmetricalCrossSection:
        if isinstance(cross_section, str):
            return self.cross_sections[cross_section]
        if isinstance(cross_section, TCrossSection):
            cross_section = cross_section.base
        if isinstance(cross_section, SymmetricalCrossSection):
            if cross_section.enclosure != self.kcl.get_enclosure(
                cross_section.enclosure
            ):
                return self.get_cross_section(
                    SymmetricalCrossSection(
                        enclosure=self.kcl.layer_enclosures.get_enclosure(
                            LayerEnclosureSpec(
                                sections=cross_section.enclosure.model_dump()[
                                    "sections"
                                ],
                                main_layer=cross_section.main_layer,
                                name=cross_section.enclosure._name,
                            ),
                            kcl=self.kcl,
                        ),
                        name=cross_section.name,
                        width=cross_section.width,
                    )
                )
        elif isinstance(cross_section, DSymmetricalCrossSection):
            cross_section = cross_section.to_itype(self.kcl)

        elif cross_section.get("unit", "dbu") == "dbu":
            cross_section = SymmetricalCrossSection(
                width=cross_section["width"],  # type: ignore[arg-type]
                enclosure=self.kcl.layer_enclosures.get_enclosure(
                    LayerEnclosureSpec(
                        sections=cross_section.get("sections", []),  # type: ignore[typeddict-item]
                        main_layer=cross_section["layer"],
                        name=cross_section.get("enclosure", {}).get("name"),  # type: ignore[attr-defined]
                    ),
                    kcl=self.kcl,
                ),
                name=cross_section.get("name", None),
            )
        else:
            cross_section = SymmetricalCrossSection(
                width=self.kcl.to_dbu(cross_section["width"]),
                enclosure=self.kcl.layer_enclosures.get_enclosure(
                    LayerEnclosureSpec(
                        dsections=[
                            (section[0], self.kcl.to_dbu(section[1]))
                            if len(section) == 2  # noqa: PLR2004
                            else (
                                section[0],
                                self.kcl.to_dbu(section[1]),
                                self.kcl.to_dbu(section[2]),
                            )
                            for section in cross_section.get("sections", [])
                        ],
                        main_layer=cross_section["layer"],
                        name=cross_section.get("enclosure", {}).get("name"),  # type: ignore[attr-defined]
                    ),
                    kcl=self.kcl,
                ),
                name=cross_section.get("name", None),
            )
        if cross_section.name not in self.cross_sections:
            self.cross_sections[cross_section.name] = cross_section
            return cross_section
        xs = self.cross_sections[cross_section.name]
        if not xs == cross_section:
            raise ValueError(
                "There is already a cross_section defined with name "
                f"{cross_section.name}. Cannot overwrite cross_sections.\n"
                f"old_xs={xs.model_dump()}\nnew_xs={cross_section.model_dump()}"
            )
        return xs

    def __repr__(self) -> str:
        return repr(self.cross_sections)
