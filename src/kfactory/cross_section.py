"""CrossSections for KFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NotRequired,
    Self,
    TypedDict,
    overload,
)

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from .enclosure import DLayerEnclosure, LayerEnclosure, LayerEnclosureSpec
from .typings import dbu  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from . import kdb
    from .layout import KCLayout

__all__ = [
    "AnyCrossSection",
    "AnyCrossSectionInput",
    "AsymmetricCrossSection",
    "AsymmetricalCrossSection",
    "CrossSection",
    "CrossSectionLayer",
    "CrossSectionSpec",
    "DAsymmetricCrossSection",
    "DAsymmetricalCrossSection",
    "DCrossSection",
    "DCrossSectionLayer",
    "DCrossSectionSpec",
    "SymmetricalCrossSection",
]


class SymmetricalCrossSection(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """CrossSection which is symmetrical to its main_layer/width."""

    width: dbu
    enclosure: LayerEnclosure
    name: str = ""
    radius: dbu | None = None
    radius_min: dbu | None = None
    bbox_sections: dict[kdb.LayerInfo, dbu]

    def __init__(
        self,
        width: dbu,
        enclosure: LayerEnclosure,
        name: str | None = None,
        bbox_sections: dict[kdb.LayerInfo, dbu] | None = None,
        radius: dbu | None = None,
        radius_min: dbu | None = None,
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

    def auto_name(self) -> str:
        return f"{self.enclosure.name}_{self.width}"

    @property
    def extent(self) -> dbu:
        return 0

    @model_validator(mode="before")
    @classmethod
    def _set_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
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

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return True

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

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return True

    def to_itype(self, kcl: KCLayout) -> SymmetricalCrossSection:
        """Convert to a dbu based CrossSection."""
        return SymmetricalCrossSection(
            width=kcl.to_dbu(self.width),
            enclosure=kcl.get_enclosure(self.enclosure.to_itype(kcl)),
            name=self.name,
        )


class CrossSectionLayer(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """Single strip in an asymmetrical cross section.

    A strip on `layer` spanning `[section_min, section_max]` in dbu relative to
    the port centerline (`offset=0`). Both bounds are signed integer dbu, so
    edges are always grid-aligned. The strip's width is the derived
    `section_max - section_min`.
    """

    layer: kdb.LayerInfo
    section_min: dbu
    section_max: dbu

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.section_min >= self.section_max:
            raise ValueError(
                "section_min must be strictly less than section_max (got"
                f" section_min={self.section_min},"
                f" section_max={self.section_max})."
            )
        return self

    @property
    def width(self) -> int:
        """Width of the strip in dbu (`section_max - section_min`)."""
        return self.section_max - self.section_min

    def _sort_key(self) -> tuple[str, int, int, int, int]:
        return (
            self.layer.name,
            self.layer.layer,
            self.layer.datatype,
            self.section_min,
            self.section_max,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CrossSectionLayer):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, CrossSectionLayer):
            return NotImplemented
        return self._sort_key() <= other._sort_key()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, CrossSectionLayer):
            return NotImplemented
        return self._sort_key() > other._sort_key()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, CrossSectionLayer):
            return NotImplemented
        return self._sort_key() >= other._sort_key()


class DCrossSectionLayer(BaseModel, arbitrary_types_allowed=True):
    """um based CrossSectionLayer."""

    layer: kdb.LayerInfo
    section_min: float
    section_max: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.section_min >= self.section_max:
            raise ValueError(
                "section_min must be strictly less than section_max (got"
                f" section_min={self.section_min},"
                f" section_max={self.section_max})."
            )
        return self

    @property
    def width(self) -> float:
        """Width of the strip in um (`section_max - section_min`)."""
        return self.section_max - self.section_min

    def to_itype(self, kcl: KCLayout) -> CrossSectionLayer:
        return CrossSectionLayer(
            layer=self.layer,
            section_min=kcl.to_dbu(self.section_min),
            section_max=kcl.to_dbu(self.section_max),
        )


def _layer_sort_key(layer: kdb.LayerInfo) -> tuple[str, int, int]:
    return (layer.name, layer.layer, layer.datatype)


def _normalize_sections(
    sections: Sequence[CrossSectionLayer] | tuple[CrossSectionLayer, ...],
) -> tuple[CrossSectionLayer, ...]:
    """Canonicalize a section list.

    Sections on the same layer that touch or overlap are merged into a single
    strip spanning their combined extent. Output is sorted by
    (layer.name, layer.layer, layer.datatype, section_min).
    """
    by_layer: dict[tuple[str, int, int], list[CrossSectionLayer]] = {}
    layer_for_key: dict[tuple[str, int, int], kdb.LayerInfo] = {}
    for s in sections:
        key = _layer_sort_key(s.layer)
        by_layer.setdefault(key, []).append(s)
        layer_for_key.setdefault(key, s.layer)

    merged: list[CrossSectionLayer] = []
    for key in sorted(by_layer.keys()):
        strips = sorted(by_layer[key], key=lambda s: (s.section_min, s.section_max))
        run_min = strips[0].section_min
        run_max = strips[0].section_max
        for s in strips[1:]:
            if s.section_min <= run_max:
                run_max = max(run_max, s.section_max)
            else:
                merged.append(
                    CrossSectionLayer(
                        layer=layer_for_key[key],
                        section_min=run_min,
                        section_max=run_max,
                    )
                )
                run_min = s.section_min
                run_max = s.section_max
        merged.append(
            CrossSectionLayer(
                layer=layer_for_key[key],
                section_min=run_min,
                section_max=run_max,
            )
        )
    return tuple(merged)


class AsymmetricalCrossSection(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """Cross section composed of independent layer strips at signed bounds.

    The main strip (`layer`, `section_min`, `section_max`) is the port
    reference; `sections` holds any additional strips. All bounds are signed
    integer dbu relative to the port centerline (`x = 0`). Strip edges are
    always grid-aligned regardless of width parity.
    """

    layer: kdb.LayerInfo
    section_min: dbu
    section_max: dbu
    sections: tuple[CrossSectionLayer, ...] = ()
    name: str = ""
    radius: dbu | None = None
    radius_min: dbu | None = None
    bbox_sections: dict[kdb.LayerInfo, dbu] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        sections = data.get("sections", ())
        coerced: list[CrossSectionLayer] = []
        for s in sections:
            if isinstance(s, CrossSectionLayer):
                coerced.append(s)
            else:
                coerced.append(CrossSectionLayer.model_validate(s))
        data["sections"] = _normalize_sections(coerced)
        if not data.get("name"):
            layer = data["layer"]
            data["name"] = (
                f"asym_{layer.name or layer.layer}"
                f"_{data['section_min']}_{data['section_max']}"
            )
        return data

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.section_min >= self.section_max:
            raise ValueError(
                "section_min must be strictly less than section_max"
                f" (got section_min={self.section_min},"
                f" section_max={self.section_max})."
            )
        return self

    @property
    def width(self) -> int:
        """Main strip width in dbu (`section_max - section_min`)."""
        return self.section_max - self.section_min

    @property
    def main_layer(self) -> kdb.LayerInfo:
        """Main layer of the cross section (parity with SymmetricalCrossSection)."""
        return self.layer

    def to_dtype(self, kcl: KCLayout) -> DAsymmetricalCrossSection:
        return DAsymmetricalCrossSection(
            layer=self.layer,
            section_min=kcl.to_um(self.section_min),
            section_max=kcl.to_um(self.section_max),
            sections=tuple(
                DCrossSectionLayer(
                    layer=s.layer,
                    section_min=kcl.to_um(s.section_min),
                    section_max=kcl.to_um(s.section_max),
                )
                for s in self.sections
            ),
            name=self.name,
            radius=kcl.to_um(self.radius) if self.radius is not None else None,
            radius_min=kcl.to_um(self.radius_min)
            if self.radius_min is not None
            else None,
            bbox_sections={k: kcl.to_um(v) for k, v in self.bbox_sections.items()},
        )

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return False

    def _all_strips(self) -> tuple[tuple[int, int], ...]:
        """Return (section_min, section_max) for main + every aux section."""
        return (
            (self.section_min, self.section_max),
            *((s.section_min, s.section_max) for s in self.sections),
        )

    def get_xmin(self) -> int:
        return min(lo for lo, _ in self._all_strips())

    def get_xmax(self) -> int:
        return max(hi for _, hi in self._all_strips())

    def model_copy(
        self, *, update: Mapping[str, Any] | None = {"name": None}, deep: bool = False
    ) -> AsymmetricalCrossSection:
        return super().model_copy(update=update, deep=deep)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, TAsymmetricCrossSection):
            return o == self
        return super().__eq__(o)

    def __hash__(self) -> int:
        return hash(
            (
                self.layer,
                self.section_min,
                self.section_max,
                self.sections,
                self.name,
                self.radius,
                self.radius_min,
                tuple(sorted(self.bbox_sections.items(), key=lambda kv: kv[0].name)),
            )
        )

    def _sort_key(
        self,
    ) -> tuple[
        str, int, int, int, int, tuple[tuple[str, int, int, int, int], ...], str
    ]:
        return (
            self.layer.name,
            self.layer.layer,
            self.layer.datatype,
            self.section_min,
            self.section_max,
            tuple(s._sort_key() for s in self.sections),
            self.name,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, AsymmetricalCrossSection):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, AsymmetricalCrossSection):
            return NotImplemented
        return self._sort_key() <= other._sort_key()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, AsymmetricalCrossSection):
            return NotImplemented
        return self._sort_key() > other._sort_key()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, AsymmetricalCrossSection):
            return NotImplemented
        return self._sort_key() >= other._sort_key()


class DAsymmetricalCrossSection(BaseModel, arbitrary_types_allowed=True):
    """um based AsymmetricalCrossSection."""

    layer: kdb.LayerInfo
    section_min: float
    section_max: float
    sections: tuple[DCrossSectionLayer, ...] = ()
    name: str | None = None
    radius: float | None = None
    radius_min: float | None = None
    bbox_sections: dict[kdb.LayerInfo, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.section_min >= self.section_max:
            raise ValueError(
                "section_min must be strictly less than section_max"
                f" (got section_min={self.section_min},"
                f" section_max={self.section_max})."
            )
        return self

    @property
    def width(self) -> float:
        """Main strip width in um (`section_max - section_min`)."""
        return self.section_max - self.section_min

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return False

    def to_itype(self, kcl: KCLayout) -> AsymmetricalCrossSection:
        return AsymmetricalCrossSection(
            layer=self.layer,
            section_min=kcl.to_dbu(self.section_min),
            section_max=kcl.to_dbu(self.section_max),
            sections=tuple(s.to_itype(kcl) for s in self.sections),
            name=self.name or "",
            radius=kcl.to_dbu(self.radius) if self.radius is not None else None,
            radius_min=kcl.to_dbu(self.radius_min)
            if self.radius_min is not None
            else None,
            bbox_sections={k: kcl.to_dbu(v) for k, v in self.bbox_sections.items()},
        )


type AnyCrossSection = SymmetricalCrossSection | AsymmetricalCrossSection
type AnyCrossSectionInput = (
    SymmetricalCrossSection
    | AsymmetricalCrossSection
    | TCrossSection[Any]
    | TAsymmetricCrossSection[Any]
)


class TAsymmetricCrossSection[T: (int, float)](ABC):
    """Unit-flavored wrapper around an `AsymmetricalCrossSection` base.

    Mirrors `TCrossSection` for the symmetric case: both the dbu wrapper
    (`AsymmetricCrossSection`) and the um wrapper (`DAsymmetricCrossSection`)
    hold the same `AsymmetricalCrossSection` as `_base`, so they compare equal
    across units via `.base`.
    """

    _base: AsymmetricalCrossSection = PrivateAttr()
    kcl: KCLayout

    @property
    def base(self) -> AsymmetricalCrossSection:
        return self._base

    @property
    def name(self) -> str:
        return self._base.name

    @property
    def layer(self) -> kdb.LayerInfo:
        return self._base.layer

    @property
    def main_layer(self) -> kdb.LayerInfo:
        return self._base.layer

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return False

    @property
    @abstractmethod
    def width(self) -> T: ...

    @property
    @abstractmethod
    def section_min(self) -> T: ...

    @property
    @abstractmethod
    def section_max(self) -> T: ...

    @property
    @abstractmethod
    def sections(
        self,
    ) -> tuple[CrossSectionLayer, ...] | tuple[DCrossSectionLayer, ...]: ...

    @property
    @abstractmethod
    def radius(self) -> T | None: ...

    @property
    @abstractmethod
    def radius_min(self) -> T | None: ...

    @property
    @abstractmethod
    def bbox_sections(self) -> dict[kdb.LayerInfo, T]: ...

    @abstractmethod
    def get_xmin_xmax(self) -> tuple[T, T]: ...

    def to_itype(self) -> AsymmetricCrossSection:
        return AsymmetricCrossSection(kcl=self.kcl, base=self._base)

    def to_dtype(self) -> DAsymmetricCrossSection:
        return DAsymmetricCrossSection(kcl=self.kcl, base=self._base)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, TAsymmetricCrossSection):
            return self.base == o.base
        if isinstance(o, AsymmetricalCrossSection):
            return self.base == o
        return False

    def __hash__(self) -> int:
        return hash(self._base)


class AsymmetricCrossSection(TAsymmetricCrossSection[int]):
    """dbu-flavored wrapper around an `AsymmetricalCrossSection`."""

    @overload
    def __init__(self, kcl: KCLayout, *, base: AsymmetricalCrossSection) -> None: ...

    @overload
    def __init__(
        self,
        kcl: KCLayout,
        section_min: int,
        section_max: int,
        layer: kdb.LayerInfo,
        sections: Sequence[CrossSectionLayer] = (),
        name: str | None = None,
        radius: int | None = None,
        radius_min: int | None = None,
        bbox_sections: dict[kdb.LayerInfo, int] | None = None,
    ) -> None: ...

    def __init__(
        self,
        kcl: KCLayout,
        section_min: int | None = None,
        section_max: int | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: Sequence[CrossSectionLayer] = (),
        name: str | None = None,
        radius: int | None = None,
        radius_min: int | None = None,
        bbox_sections: dict[kdb.LayerInfo, int] | None = None,
        base: AsymmetricalCrossSection | None = None,
    ) -> None:
        if base is None:
            if section_min is None or section_max is None or layer is None:
                raise ValueError(
                    "If no base is given, section_min, section_max, and layer"
                    " must be defined"
                )
            base = kcl.get_asymmetrical_cross_section(
                AsymmetricalCrossSection(
                    layer=layer,
                    section_min=section_min,
                    section_max=section_max,
                    sections=tuple(sections),
                    name=name or "",
                    radius=radius,
                    radius_min=radius_min,
                    bbox_sections=bbox_sections or {},
                )
            )
        self.kcl = kcl
        self._base = base

    @property
    def width(self) -> int:
        return self._base.width

    @property
    def section_min(self) -> int:
        return self._base.section_min

    @property
    def section_max(self) -> int:
        return self._base.section_max

    @property
    def sections(self) -> tuple[CrossSectionLayer, ...]:
        return self._base.sections

    @property
    def radius(self) -> int | None:
        return self._base.radius

    @property
    def radius_min(self) -> int | None:
        return self._base.radius_min

    @property
    def bbox_sections(self) -> dict[kdb.LayerInfo, int]:
        return self._base.bbox_sections.copy()

    def get_xmin_xmax(self) -> tuple[int, int]:
        return (self._base.get_xmin(), self._base.get_xmax())


class DAsymmetricCrossSection(TAsymmetricCrossSection[float]):
    """um-flavored wrapper around an `AsymmetricalCrossSection`."""

    @overload
    def __init__(self, kcl: KCLayout, *, base: AsymmetricalCrossSection) -> None: ...

    @overload
    def __init__(
        self,
        kcl: KCLayout,
        section_min: float,
        section_max: float,
        layer: kdb.LayerInfo,
        sections: Sequence[DCrossSectionLayer] = (),
        name: str | None = None,
        radius: float | None = None,
        radius_min: float | None = None,
        bbox_sections: dict[kdb.LayerInfo, float] | None = None,
    ) -> None: ...

    def __init__(
        self,
        kcl: KCLayout,
        section_min: float | None = None,
        section_max: float | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: Sequence[DCrossSectionLayer] = (),
        name: str | None = None,
        radius: float | None = None,
        radius_min: float | None = None,
        bbox_sections: dict[kdb.LayerInfo, float] | None = None,
        base: AsymmetricalCrossSection | None = None,
    ) -> None:
        if base is None:
            if section_min is None or section_max is None or layer is None:
                raise ValueError(
                    "If no base is given, section_min, section_max, and layer"
                    " must be defined"
                )
            base = kcl.get_asymmetrical_cross_section(
                DAsymmetricalCrossSection(
                    layer=layer,
                    section_min=section_min,
                    section_max=section_max,
                    sections=tuple(sections),
                    name=name,
                    radius=radius,
                    radius_min=radius_min,
                    bbox_sections=bbox_sections or {},
                ).to_itype(kcl)
            )
        self.kcl = kcl
        self._base = base

    @property
    def width(self) -> float:
        return self.kcl.to_um(self._base.width)

    @property
    def section_min(self) -> float:
        return self.kcl.to_um(self._base.section_min)

    @property
    def section_max(self) -> float:
        return self.kcl.to_um(self._base.section_max)

    @property
    def sections(self) -> tuple[DCrossSectionLayer, ...]:
        return tuple(
            DCrossSectionLayer(
                layer=s.layer,
                section_min=self.kcl.to_um(s.section_min),
                section_max=self.kcl.to_um(s.section_max),
            )
            for s in self._base.sections
        )

    @property
    def radius(self) -> float | None:
        r = self._base.radius
        return self.kcl.to_um(r) if r is not None else None

    @property
    def radius_min(self) -> float | None:
        r = self._base.radius_min
        return self.kcl.to_um(r) if r is not None else None

    @property
    def bbox_sections(self) -> dict[kdb.LayerInfo, float]:
        return {k: self.kcl.to_um(v) for k, v in self._base.bbox_sections.items()}

    def get_xmin_xmax(self) -> tuple[float, float]:
        return (
            self.kcl.to_um(self._base.get_xmin()),
            self.kcl.to_um(self._base.get_xmax()),
        )


class TCrossSection[T: (int, float)](ABC):
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
        width: T,
        layer: kdb.LayerInfo,
        sections: Sequence[tuple[T, T] | tuple[T]],
        radius: T | None = None,
        radius_min: T | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[T] | None = None,
    ) -> None: ...

    @abstractmethod
    def __init__(
        self,
        kcl: KCLayout,
        width: T | None = None,
        layer: kdb.LayerInfo | None = None,
        sections: Sequence[tuple[T, T] | tuple[T]] | None = None,
        radius: T | None = None,
        radius_min: T | None = None,
        bbox_layers: Sequence[kdb.LayerInfo] | None = None,
        bbox_offsets: Sequence[T] | None = None,
        base: SymmetricalCrossSection | None = None,
    ) -> None: ...

    @property
    def base(self) -> SymmetricalCrossSection:
        return self._base

    @property
    @abstractmethod
    def width(self) -> T: ...

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
    def sections(self) -> dict[kdb.LayerInfo, list[tuple[T | None, T]]]: ...

    @property
    @abstractmethod
    def radius(self) -> T | None: ...

    @property
    @abstractmethod
    def radius_min(self) -> T | None: ...

    @property
    @abstractmethod
    def bbox_sections(
        self,
    ) -> dict[kdb.LayerInfo, T]: ...

    @abstractmethod
    def get_xmin_xmax(self) -> tuple[T, T]: ...

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

    @property
    def main_layer(self) -> kdb.LayerInfo:
        """Main Layer of the enclosure and cross section."""
        return self.base.main_layer

    def is_symmetric(self) -> bool:
        """Whether this cross section is symmetric."""
        return True


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
                            (s[0], *[kcl.to_dbu(s[i]) for i in range(1, len(s))])  # ty:ignore[no-matching-overload]
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


class TCrossSectionSpec[T: (int, float)](TypedDict):
    name: NotRequired[str]
    sections: NotRequired[list[tuple[kdb.LayerInfo, T] | tuple[kdb.LayerInfo, T, T]]]
    layer: kdb.LayerInfo
    width: T
    bbox_layers: NotRequired[Sequence[kdb.LayerInfo]]
    bbox_offsets: NotRequired[Sequence[T]]


class CrossSectionSpec(TCrossSectionSpec[int]):
    unit: NotRequired[Literal["dbu"]]


class DCrossSectionSpec(TCrossSectionSpec[float]):
    unit: Literal["um"]


class CrossSectionModel(BaseModel):
    cross_sections: dict[str, SymmetricalCrossSection] = Field(default_factory=dict)
    asymmetrical_cross_sections: dict[str, AsymmetricalCrossSection] = Field(
        default_factory=dict
    )
    kcl: KCLayout

    def __getitem__(self, name: str) -> SymmetricalCrossSection:
        return self.cross_sections[name]

    def get_asymmetrical_cross_section(
        self,
        cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection,
    ) -> AsymmetricalCrossSection:
        if isinstance(cross_section, str):
            return self.asymmetrical_cross_sections[cross_section]
        if isinstance(cross_section, DAsymmetricalCrossSection):
            cross_section = cross_section.to_itype(self.kcl)
        if cross_section.name in self.cross_sections:
            raise ValueError(
                f"Name {cross_section.name!r} is already used by a symmetric"
                " cross section. Cross section names must be unique across"
                " symmetric and asymmetric kinds."
            )
        if cross_section.name not in self.asymmetrical_cross_sections:
            self.asymmetrical_cross_sections[cross_section.name] = cross_section
            return cross_section
        xs = self.asymmetrical_cross_sections[cross_section.name]
        if xs != cross_section:
            raise ValueError(
                "There is already an asymmetrical cross_section defined with name "
                f"{cross_section.name}. Cannot overwrite cross_sections.\n"
                f"old_xs={xs.model_dump()}\nnew_xs={cross_section.model_dump()}"
            )
        return xs

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
                width=cross_section["width"],  # ty:ignore[invalid-argument-type]
                enclosure=self.kcl.layer_enclosures.get_enclosure(
                    LayerEnclosureSpec(
                        sections=cross_section.get("sections", []),  # ty:ignore[invalid-argument-type]
                        main_layer=cross_section["layer"],
                        name=cross_section.get("enclosure", {}).get("name"),
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
                        sections=[
                            (section[0], self.kcl.to_dbu(section[1]))
                            if len(section) == 2
                            else (
                                section[0],
                                self.kcl.to_dbu(section[1]),
                                self.kcl.to_dbu(section[2]),  # ty:ignore[index-out-of-bounds]
                            )
                            for section in cross_section.get("sections", [])
                        ],
                        main_layer=cross_section["layer"],
                        name=cross_section.get("enclosure", {}).get("name"),
                    ),
                    kcl=self.kcl,
                ),
                name=cross_section.get("name", None),
            )
        if cross_section.name in self.asymmetrical_cross_sections:
            raise ValueError(
                f"Name {cross_section.name!r} is already used by an asymmetric"
                " cross section. Cross section names must be unique across"
                " symmetric and asymmetric kinds."
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
