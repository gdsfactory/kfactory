"""Enclosure module.

[Enclosures][kfactory.enclosure.LayerEnclosure] allow to calculate slab/excludes and
similar concepts to an arbitrary shape located on a main_layer or reference layer or
region.
"""

from __future__ import annotations

import itertools
import sys
from collections import defaultdict
from enum import IntEnum
from functools import lru_cache
from hashlib import sha1
from typing import (
    TYPE_CHECKING,
    Any,
    NotRequired,
    TypeGuard,
    overload,
)

import numpy as np
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    RootModel,
    field_validator,
    model_serializer,
)
from typing_extensions import TypedDict

from . import kdb
from .conf import config, logger

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        Iterable,
        Mapping,
        Sequence,
    )

    from .kcell import KCell
    from .layout import KCLayout
    from .port import Port

__all__ = [
    "KCellEnclosure",
    "LayerEnclosure",
    "extrude_path",
    "extrude_path_dynamic",
    "extrude_path_dynamic_points",
    "extrude_path_points",
]


class Direction(IntEnum):
    """Direction for applying standard minkowski sums.

    Attributes:
        X: Only apply in x-direction.
        Y: Only apply in y-direction.
        BOTH: Apply in both x/y-direction. Equivalent to a
            minkowski sum with a square.
    """

    X = 1
    Y = 2
    BOTH = 3


_min_size = -sys.maxsize - 1


def is_callable_widths(
    widths: Callable[[float], float] | list[float],
) -> TypeGuard[Callable[[float], float]]:
    """Determines whether a width object is callable or a list."""
    return callable(widths)


def path_pts_to_polygon(
    pts_top: list[kdb.DPoint], pts_bot: list[kdb.DPoint]
) -> kdb.DPolygon:
    """Convert a list of points to a polygon."""
    pts_bot.reverse()
    return kdb.DPolygon(pts_top + pts_bot)


def extrude_path_points(
    path: Sequence[kdb.DPoint],
    width: float,
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """Extrude a path from a list of points and a static width.

    Args:
        path: list of floating-points points
        width: width in um
        start_angle: optionally specify a custom starting angle if `None` will
            be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None`
            will be autocalculated from the last two elements
    """
    start = path[1] - path[0]
    end = path[-1] - path[-2]
    if start_angle is None:
        start_angle = np.rad2deg(np.arctan2(start.y, start.x))
    if end_angle is None:
        end_angle = np.rad2deg(np.rad2deg(np.arctan2(end.y, end.x)))

    p_start = path[0]
    p_end = path[-1]
    start_trans = kdb.DCplxTrans(1, start_angle, False, p_start.x, p_start.y)
    end_trans = kdb.DCplxTrans(1, end_angle, False, p_end.x, p_end.y)

    ref_vector = kdb.DCplxTrans(kdb.DVector(0, width / 2))
    vector_top = [start_trans * ref_vector]
    vector_bot = [(start_trans * kdb.DCplxTrans.R180) * ref_vector]

    p_old = path[0]
    p = path[1]

    for point in path[2:]:
        p_new = point
        v = p_new - p_old
        angle = np.rad2deg(np.arctan2(v.y, v.x))
        transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
        vector_top.append(transformation * ref_vector)
        vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
        p_old = p
        p = p_new

    vector_top.append(end_trans * ref_vector)
    vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    return [v.disp.to_p() for v in vector_top], [v.disp.to_p() for v in vector_bot]


def extrude_path(
    target: KCell,
    layer: kdb.LayerInfo,
    path: list[kdb.DPoint],
    width: float,
    enclosure: LayerEnclosure | None = None,
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> kdb.DPolygon:
    """Extrude a path from a list of points and a static width.

    Args:
        target: the cell where to insert the shapes to (and get the database unit from)
        layer: the main layer that should be extruded
        path: list of floating-points points
        width: width in um
        enclosure: optional enclosure object, specifying necessary
            layers.this will extrude around the `layer`
        start_angle: optionally specify a custom starting angle if `None`
            will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be
            autocalculated from the last two elements
    """
    layer_list = {layer: LayerSection(sections=[Section(d_max=0)])}
    j = 0
    if enclosure is not None:
        if layer not in enclosure.layer_sections:
            layer_list |= enclosure.layer_sections
            j = 0
        else:
            layer_list = enclosure.layer_sections.copy()
            j = layer_list[layer].add_section(Section(d_max=0))

    for _layer, layer_sec in layer_list.items():
        reg = kdb.Region()
        for i, section in enumerate(layer_sec.sections):
            path_ = path_pts_to_polygon(
                *extrude_path_points(
                    path,
                    width + 2 * section.d_max * target.kcl.dbu,
                    start_angle,
                    end_angle,
                )
            )
            r = kdb.Region(target.kcl.to_dbu(path_))
            if section.d_min is not None:
                path_ = path_pts_to_polygon(
                    *extrude_path_points(
                        path,
                        width + 2 * section.d_min * target.kcl.dbu,
                        start_angle,
                        end_angle,
                    )
                )
                r -= kdb.Region(target.kcl.to_dbu(path_))
            reg.insert(r)
            if _layer == layer and i == j:
                ret_path = path_
        target.shapes(target.kcl.layer(_layer)).insert(reg.merge())
    return ret_path


def extrude_path_dynamic_points(
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """Extrude a profile with a list of points and a list of widths.

    Args:
        path: list of floating-points points
        widths: function (from t==0 to t==1) defining a width profile for the path
            | list with width for the profile (needs same length as path)
        start_angle: optionally specify a custom starting angle if `None` will be
            autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be
            autocalculated from the last two elements
    """
    start = path[1] - path[0]
    end = path[-1] - path[-2]
    if start_angle is None:
        start_angle = np.rad2deg(np.arctan2(start.y, start.x))
    if end_angle is None:
        end_angle = np.rad2deg(np.rad2deg(np.arctan2(end.y, end.x)))

    p_start = path[0]
    p_end = path[-1]

    start_trans = kdb.DCplxTrans(1, start_angle, False, p_start.x, p_start.y)
    end_trans = kdb.DCplxTrans(1, end_angle, False, p_end.x, p_end.y)

    if callable(widths):
        length = sum(((p2 - p1).abs() for p2, p1 in itertools.pairwise(path)))
        z: float = 0
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / length) / 2))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        z += (p - p_old).abs()
        for point in path[2:]:
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / length) / 2))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            z += (p_new - p).abs()
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / length) / 2))
    else:
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[0] / 2))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        for point, w in zip(path[2:], widths[1:-1], strict=False):
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, w / 2))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[-1] / 2))
    vector_top.append(end_trans * ref_vector)
    vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    return [v.disp.to_p() for v in vector_top], [v.disp.to_p() for v in vector_bot]


def extrude_path_dynamic(
    target: KCell,
    layer: kdb.LayerInfo,
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    enclosure: LayerEnclosure | None = None,
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> None:
    """Extrude a path with dynamic width.

    Extrude from a list of points and a list of widths and add an enclosure if
        specified.

    Args:
        target: the cell where to insert the shapes to (and get the database unit from)
        layer: the main layer that should be extruded
        path: list of floating-points points
        widths: function (from t==0 to t==1) defining a width profile for the path |
            list with width for the profile (needs same length as path)
        enclosure: optional enclosure object, specifying necessary layers.this will
            extrude around the `layer`
        start_angle: optionally specify a custom starting angle if `None` will be
            autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be
            autocalculated from the last two elements
    """
    layer_list = {layer: LayerSection(sections=[Section(d_max=0)])}
    if enclosure is not None:
        if layer not in enclosure.layer_sections:
            layer_list.update(enclosure.layer_sections)
        else:
            layer_list[layer].sections.copy()
            layer_list = enclosure.layer_sections.copy()
            for section in layer_list[layer].sections:
                layer_list[layer].add_section(section)
    if is_callable_widths(widths):
        for layer_, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:

                def w_max(x: float, section: Section = section) -> float:
                    assert section.d_max is not None
                    return widths(x) + 2 * section.d_max * target.kcl.layout.dbu

                r = kdb.Region(
                    target.kcl.to_dbu(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                w_max,
                                start_angle,
                                end_angle,
                            )
                        )
                    )
                )
                if section.d_min is not None:

                    def w_min(x: float, section: Section = section) -> float:
                        assert section.d_min is not None
                        return widths(x) + 2 * section.d_min * target.kcl.layout.dbu

                    r -= kdb.Region(
                        target.kcl.to_dbu(
                            path_pts_to_polygon(
                                *extrude_path_dynamic_points(
                                    path,
                                    w_min,
                                    start_angle,
                                    end_angle,
                                )
                            )
                        )
                    )
                reg.insert(r)
            target.shapes(target.kcl.layer(layer_)).insert(reg.merge())

    else:
        for layer_, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:
                max_widths = [
                    w + 2 * section.d_max * target.kcl.dbu
                    for w in widths  # type: ignore[union-attr]
                ]
                r = kdb.Region(
                    target.kcl.to_dbu(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                max_widths,
                                start_angle,
                                end_angle,
                            )
                        )
                    )
                )
                if section.d_min is not None:
                    min_widths = [
                        w + 2 * section.d_min * target.kcl.dbu
                        for w in widths  # type: ignore[union-attr]
                    ]
                    r -= kdb.Region(
                        target.kcl.to_dbu(
                            path_pts_to_polygon(
                                *extrude_path_dynamic_points(
                                    path,
                                    min_widths,
                                    start_angle,
                                    end_angle,
                                )
                            )
                        )
                    )
                reg.insert(r)
            target.shapes(target.kcl.layer(layer_)).insert(reg.merge())


class Section(BaseModel):
    """Section of an Enclosure.

        Maximum only Section:
            ┌────────────────────────┐  ▲
            │                        │  │
            │  ┌──────────────────┐  │  │
            │  │                  │  │  │
            │  │    Reference     │  │  │ Section
            │  │                  │  │  │ (d_max only)
            │  └─────────────┬────┘  │  │
            │                │d_max  │  │
            └────────────────▼───────┘  ▼


        Minimum & Maximum Section:
            ┌─────────────────┐
            │     Section     │
            │  ┌───────────┐  │
            │  │           │  │
            │  │  ┌─────┐  │◄─┼──d_min
            │  │  │ Ref │  │  │
            │  │  └─────┘  │  │
            │  │           │  │◄─d_max
            │  └───────────┘  │
            │                 │
            └─────────────────┘

    Attributes:
        d_min: Start of the section. If `None`,
            the section will span all the way between the maxes.
        d_max: the maximum extent of the section from the reference.
    """

    d_min: int | None = None
    d_max: int

    def __hash__(self) -> int:
        """Hash of the section."""
        return hash((self.d_min, self.d_max))


class LayerSection(BaseModel):
    """A collection of sections intended for a layer.

    Adding a section will trigger an evaluation to merge
    touching or overlapping sections.
    """

    sections: list[Section] = Field(default_factory=list)

    def add_section(self, sec: Section) -> int:
        """Add a new section.

        Checks for overlaps after.
        """
        if not self.sections:
            self.sections.append(sec)
            return 0
        i = 0
        if sec.d_min is not None:
            while i < len(self.sections) and sec.d_min > self.sections[i].d_max:
                i += 1
            while (
                i < len(self.sections) and sec.d_max >= self.sections[i].d_min  # type: ignore[operator]
            ):
                sec.d_max = max(self.sections[i].d_max, sec.d_max)
                sec.d_min = min(
                    self.sections[i].d_min,
                    sec.d_min,  # type: ignore[type-var]
                )
                self.sections.pop(i)
                if i == len(self.sections):
                    break
        self.sections.insert(i, sec)
        return i

    def max_size(self) -> int:
        """Maximum size of the sections in this layer section."""
        return self.sections[-1].d_max

    def __hash__(self) -> int:
        """Unique hash of LayerSection."""
        return hash(tuple((s.d_min, s.d_max) for s in self.sections))

    def __len__(self) -> int:
        return len(self.sections)


class DLayerEnclosure(BaseModel, arbitrary_types_allowed=True):
    sections: list[tuple[kdb.LayerInfo, float] | tuple[kdb.LayerInfo, float, float]]
    name: str | None = None
    main_layer: kdb.LayerInfo

    def to_itype(self, kcl: KCLayout) -> LayerEnclosure:
        return LayerEnclosure(
            dsections=self.sections, name=self.name, main_layer=self.main_layer, kcl=kcl
        )


class LayerEnclosure(BaseModel, arbitrary_types_allowed=True, frozen=True):
    """Definitions for calculation of enclosing (or smaller) shapes of a reference.

    Attributes:
        layer_sections: Mapping of layers to their layer sections.
        main_layer: Layer which to use unless specified otherwise.
    """

    layer_sections: dict[kdb.LayerInfo, LayerSection]
    _name: str | None = PrivateAttr()
    main_layer: kdb.LayerInfo | None
    bbox_sections: dict[kdb.LayerInfo, int]

    def __init__(
        self,
        sections: Sequence[
            tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]
        ] = [],
        name: str | None = None,
        main_layer: kdb.LayerInfo | None = None,
        dsections: Sequence[
            tuple[kdb.LayerInfo, float] | tuple[kdb.LayerInfo, float, float]
        ]
        | None = None,
        bbox_sections: Sequence[tuple[kdb.LayerInfo, int]] = [],
        kcl: KCLayout | None = None,
    ) -> None:
        """Constructor of new enclosure.

        Args:
            sections: tuples containing info for the enclosure.
                Elements must be of the form (layer, max) or (layer, min, max)
            name: Optional name of the enclosure. If a name is given in the
                cell name this name will be used for enclosure arguments.
            main_layer: Main layer used if the functions don't get an explicit layer.
            dsections: Same as sections but min/max defined in um
            kcl: `KCLayout` Used for conversion dbu -> um or when copying.
                Must be specified if `desections` is not `None`. Also necessary
                if copying to another layout and not all layers used are LayerInfos.
        """
        layer_sections: dict[kdb.LayerInfo, LayerSection] = {}

        if dsections is not None:
            assert kcl is not None, "If sections in um are defined, kcl must be set"
            sections = list(sections)
            for section in dsections:
                if len(section) == 2:  # noqa: PLR2004
                    sections.append((section[0], kcl.to_dbu(section[1])))

                elif len(section) == 3:  # noqa: PLR2004
                    sections.append(
                        (
                            section[0],
                            kcl.to_dbu(section[1]),
                            kcl.to_dbu(section[2]),
                        )
                    )

        for sec in sorted(
            sections,
            key=lambda sec: (sec[0].name, sec[0].layer, sec[0].datatype, sec[1]),
        ):
            if sec[0] in layer_sections:
                ls = layer_sections[sec[0]]
            else:
                ls = LayerSection()
                layer_sections[sec[0]] = ls
            ls.add_section(Section(d_max=sec[1])) if len(sec) < 3 else ls.add_section(  # noqa: PLR2004
                Section(d_max=sec[2], d_min=sec[1])
            )
        super().__init__(
            main_layer=main_layer,
            kcl=kcl,
            layer_sections=layer_sections,
            bbox_sections={t[0]: t[1] for t in bbox_sections},
        )
        self._name = name

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sections": [
                (layer, s.d_max) if s.d_min is None else (layer, s.d_min, s.d_max)
                for layer, sections in self.layer_sections.items()
                for s in sections.sections
            ],
            "main_layer": self.main_layer,
        }

    def __hash__(self) -> int:  # make hashable BaseModel subclass
        """Calculate a unique hash of the enclosure."""
        return hash((str(self), self.main_layer, tuple(self.layer_sections.items())))

    def to_dtype(self, kcl: KCLayout) -> DLayerEnclosure:
        """Convert the enclosure to a um based enclosure."""
        if self.main_layer is None:
            raise ValueError("um based enclosures must have a main_layer")
        return DLayerEnclosure(
            name=self._name,
            sections=[
                (layer, kcl.to_um(section.d_max))
                if section.d_min is None
                else (layer, kcl.to_um(section.d_min), kcl.to_um(section.d_max))
                for layer, layer_section in self.layer_sections.items()
                for section in layer_section.sections
            ],
            main_layer=self.main_layer,
        )

    @property
    def name(self) -> str:
        """Get name of the Enclosure."""
        return self.__str__()

    def minkowski_region(
        self,
        r: kdb.Region,
        d: int | None,
        shape: Callable[[int], list[kdb.Point] | kdb.Box | kdb.Edge | kdb.Polygon],
    ) -> kdb.Region:
        """Calculaste a region from a minkowski sum.

        If the distance is negative, the function will take the inverse region and apply
        the minkowski and take the inverse again.

        Args:
            r: Target region.
            d: Distance to pass to the shape. Can be any integer. [dbu]
            shape: Function returning a shape for the minkowski region.
        """
        if d is None:
            return kdb.Region()
        if d == 0:
            return r.dup()
        if d > 0:
            return r.minkowski_sum(shape(d))
        shape_ = shape(abs(d))
        if isinstance(shape_, list):
            box_shape = kdb.Polygon(shape_)
            bbox_maxsize = max(
                box_shape.bbox().width(),
                box_shape.bbox().height(),
            )
        else:
            bbox_maxsize = max(
                shape_.bbox().width(),
                shape_.bbox().height(),
            )
        bbox_r = kdb.Region(r.bbox().enlarged(bbox_maxsize))
        return r - (bbox_r - r).minkowski_sum(shape_)

    def apply_minkowski_enc(
        self,
        c: KCell,
        ref: kdb.LayerInfo | kdb.Region | None,  # layer index or the region
        direction: Direction = Direction.BOTH,
    ) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            ref: Reference to use as a base for the enclosure.
            direction: X/Y or both directions.
                Uses a box if both directions are selected.
        """
        match direction:
            case Direction.BOTH:

                def box(d: int) -> kdb.Box:
                    return kdb.Box(-d, -d, d, d)

                self.apply_minkowski_custom(c, ref=ref, shape=box)

            case Direction.Y:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(0, -d, 0, d)

                self.apply_minkowski_custom(c, ref=ref, shape=edge)

            case Direction.X:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(-d, 0, d, 0)

                self.apply_minkowski_custom(c, ref=ref, shape=edge)

            case _:
                raise ValueError("Undefined direction")

    def apply_minkowski_y(
        self, c: KCell, ref: kdb.LayerInfo | kdb.Region | None = None
    ) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            ref: Reference to use as a base for the enclosure.
        """
        return self.apply_minkowski_enc(c, ref=ref, direction=Direction.Y)

    def apply_minkowski_x(
        self, c: KCell, ref: kdb.LayerInfo | kdb.Region | None
    ) -> None:
        """Apply an enclosure with a vector in x-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            ref: Reference to use as a base for the enclosure.
        """
        return self.apply_minkowski_enc(c, ref=ref, direction=Direction.X)

    def apply_minkowski_custom(
        self,
        c: KCell,
        shape: Callable[[int], kdb.Edge | kdb.Polygon | kdb.Box],
        ref: kdb.LayerInfo | kdb.Region | None = None,
    ) -> None:
        """Apply an enclosure with a custom shape.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            shape: A function that will return a shape which takes one argument
                the size of the section in dbu.
            ref: Reference to use as a base for the enclosure.
        """
        if ref is None:
            ref = self.main_layer

            if ref is None:
                raise ValueError(
                    "The enclosure doesn't have  a reference `main_layer` defined."
                    " Therefore the layer must be defined in calls"
                )
        r = (
            kdb.Region(c.begin_shapes_rec(c.kcl.layer(ref)))
            if isinstance(ref, kdb.LayerInfo)
            else ref.dup()
        )
        r.merge()

        for layer, layersec in reversed(self.layer_sections.items()):
            for section in layersec.sections:
                c.shapes(c.kcl.layer(layer)).insert(
                    self.minkowski_region(r, section.d_max, shape)
                    - self.minkowski_region(r, section.d_min, shape)
                )

    def apply_minkowski_tiled(
        self,
        c: KCell,
        ref: kdb.LayerInfo | kdb.Region | None = None,
        tile_size: float | None = None,
        n_pts: int = 64,
        n_threads: int | None = None,
        carve_out_ports: Iterable[Port] = [],
    ) -> None:
        """Minkowski regions with tiling processor.

        Useful if the target is a big or complicated enclosure. Will split target ref
        into tiles and calculate them in parallel. Uses a circle as a shape for the
        minkowski sum.

        Args:
            c: Target KCell to apply the enclosures into.
            ref: The reference shapes to apply the enclosures to.
                Can be a layer or a region. If `None`, it will try to use the
                `main_layer` of the
                [enclosure][kfactory.enclosure.LayerEnclosure].
            tile_size: Tile size. This should be in the order off 10+ maximum size
                of the maximum size of sections.
            n_pts: Number of points in the circle. < 3 will create a triangle. 4 a
                diamond, etc.
            n_threads: Number o threads to use. By default (`None`) it will use as many
                threads as are set to the process (usually all cores of the machine).
            carve_out_ports: Carves out a box of port_width +
        """
        if ref is None:
            ref = self.main_layer

            if ref is None:
                raise ValueError(
                    "The enclosure doesn't have  a reference `main_layer` defined."
                    " Therefore the layer must be defined in calls"
                )
        tp = kdb.TilingProcessor()
        tp.frame = c.dbbox()  # type: ignore[misc, assignment]
        tp.dbu = c.kcl.dbu
        tp.threads = n_threads or config.n_threads
        maxsize = 0
        for layersection in self.layer_sections.values():
            maxsize = max(
                maxsize, *[section.d_max for section in layersection.sections]
            )

        min_tile_size_rec = 10 * maxsize * tp.dbu

        if tile_size is None:
            tile_size = min_tile_size_rec * 2

        if float(tile_size) <= min_tile_size_rec:
            logger.warning(
                "Tile size should be larger than the maximum of "
                "the enclosures (recommendation: {} / {})",
                tile_size,
                min_tile_size_rec,
            )

        tp.tile_border(maxsize * tp.dbu, maxsize * tp.dbu)

        tp.tile_size(tile_size, tile_size)
        if isinstance(ref, kdb.LayerInfo):
            tp.input("main_layer", c.kcl.layout, c.cell_index(), c.kcl.layer(ref))
        else:
            tp.input("main_layer", ref)

        operators = []
        port_holes: dict[int, kdb.Region] = defaultdict(kdb.Region)
        ports_by_layer: dict[int, list[Port]] = defaultdict(list)
        for port in c.ports:
            ports_by_layer[port.layer].append(port)

        for layer, sections in self.layer_sections.items():
            layer_index = c.kcl.layer(layer)
            operator = RegionOperator(cell=c, layer=layer_index)
            tp.output(f"target_{layer_index}", operator)
            max_size: int = _min_size
            for _i, section in enumerate(reversed(sections.sections)):
                max_size = max(max_size, section.d_max)
                queue_str = f"var tile_reg = (_tile & _frame).sized({maxsize});"
                queue_str += (
                    "var max_shape = Polygon.ellipse("
                    f"Box.new({section.d_max * 2},{section.d_max * 2}), {n_pts});"
                )
                match section.d_max:
                    case d if d > 0:
                        max_region = (
                            "var max_reg = "
                            "main_layer.minkowski_sum(max_shape).merged();"
                        )
                    case d if d < 0:
                        max_region = "var max_reg = tile_reg - (tile_reg - main_layer);"
                    case 0:
                        max_region = "var max_reg = main_layer & tile_reg;"
                queue_str += max_region
                if section.d_min is not None:
                    queue_str += (
                        "var min_shape = Polygon.ellipse("
                        f"Box.new({section.d_min * 2},{section.d_min * 2}), 64);"
                    )
                    match section.d_min:
                        case d if d > 0:
                            min_region = (
                                "var min_reg = main_layer.minkowski_sum(min_shape);"
                            )
                        case d if d < 0:
                            min_region = (
                                "var min_reg = tile_reg - "
                                "(tile_reg - main_layer).minkowski_sum(min_shape);"
                            )
                        case 0:
                            min_region = "var min_reg = main_layer & tile_reg;"
                    queue_str += min_region
                    queue_str += (
                        f"_output(target_{layer_index},"
                        "(max_reg - min_reg)& _tile, true);"
                    )
                else:
                    queue_str += f"_output(target_{layer_index},max_reg & _tile, true);"

                tp.queue(queue_str)
                logger.debug(
                    "String queued for {} on layer {}: {}", c.name, layer, queue_str
                )

            operators.append((layer_index, operator))
            if carve_out_ports:
                r = port_holes[layer_index]
                for port in carve_out_ports:
                    if port._base.trans is not None:
                        r.insert(
                            port_hole(port.width, max_size).transformed(port.trans)
                        )
                    else:
                        r.insert(
                            port_hole(port.width, max_size).transformed(
                                kdb.ICplxTrans(port.dcplx_trans, c.kcl.dbu)
                            )
                        )
                port_holes[layer_index] = r

        c.kcl.start_changes()
        logger.info("Starting minkowski on {}", c.name)
        tp.execute(f"Minkowski {c.name}")
        c.kcl.end_changes()

        if carve_out_ports:
            for layer_index, operator in operators:
                operator.insert(port_holes=port_holes[layer_index])
        else:
            for _, operator in operators:
                operator.insert()

    def apply_custom(
        self,
        c: KCell,
        shape: Callable[
            [int, int | None], kdb.Edge | kdb.Polygon | kdb.Box | kdb.Region
        ],
    ) -> None:
        """Apply a custom shape based on the section size.

        Args:
            c: The cell to apply the enclosure to.
            shape: A function taking the section size in dbu to calculate the
                full enclosure.
        """
        for layer, layersec in self.layer_sections.items():
            layer_index = c.kcl.layer(layer)
            for sec in layersec.sections:
                c.shapes(layer_index).insert(shape(sec.d_max, sec.d_min))

    def apply_bbox(
        self, c: KCell, ref: kdb.LayerInfo | kdb.Region | None = None
    ) -> None:
        """Apply an enclosure based on a bounding box.

        Args:
            c: Target cell.
            ref: Reference layer or region (the bounding box). If `None` use
                the `main_layer` of  the
                [enclosure][kfactory.enclosure.LayerEnclosure] if defined,
                else throw an error.
        """
        if ref is None:
            ref = self.main_layer

            if ref is None:
                raise ValueError(
                    "The enclosure doesn't have  a reference `main_layer` defined."
                    " Therefore the layer must be defined in calls"
                )

        if isinstance(ref, kdb.LayerInfo):
            ref_ = c.bbox(c.kcl.layer(ref))
        elif isinstance(ref, kdb.Region):
            ref_ = ref.bbox()

        def bbox_reg(d_max: int, d_min: int | None = None) -> kdb.Region:
            reg_max = kdb.Region(ref_)
            reg_max.size(d_max)
            if d_min is None:
                return reg_max
            reg_min = kdb.Region(ref_)
            reg_min.size(d_min)
            return reg_max - reg_min

        self.apply_custom(c, bbox_reg)

    def __str__(self) -> str:
        """String representation of an enclosure.

        Use [name][kfactory.enclosure.LayerEnclosure.name]
        if available. Use a hash of the sections and main_layer if the name is `None`.
        """
        if self._name is not None:
            return self._name
        list_to_hash: Any = [
            self.main_layer,
        ]
        for layer, layer_section in self.layer_sections.items():
            list_to_hash.append([str(layer), str(layer_section.sections)])
        return sha1(str(list_to_hash).encode("UTF-8")).hexdigest()[-8:]  # noqa: S324

    def extrude_path(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: kdb.LayerInfo | None,
        width: float,
        start_angle: float | None = None,
        end_angle: float | None = None,
    ) -> None:
        """Extrude a path and add it to a main layer.

        Start and end angle should be set in relation to the orientation of the path.
        If the path for example is starting E->W, the start angle should be 0 (if that
        that is the desired angle). End angle is the same if the end
        piece is stopping 2nd-last -> last in E->W.

        Args:
            c: The cell where to insert the path to
            path: Backbone of the path. [um]
            main_layer: Layer index where to put the main part of the path.
            width: Width of the core of the path
            start_angle: angle of the start piece
            end_angle: angle of the end piece
        """
        if main_layer is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined."
                " Therefore the layer must be defined in calls"
            )
        extrude_path(
            target=c,
            layer=main_layer,
            path=path,
            width=width,
            enclosure=self,
            start_angle=start_angle,
            end_angle=end_angle,
        )

    def extrude_path_dynamic(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: kdb.LayerInfo | None,
        widths: Callable[[float], float] | list[float],
    ) -> None:
        """Extrude a path and add it to a main layer.

        Supports a dynamic width of the path defined by a function
        returning the width for the interval [0,1], or as a list of
        widths of the same lengths as the points.

        Args:
            c: The cell where to insert the path to
            path: Backbone of the path. [um]
            main_layer: Layer index where to put the main part of the path.
            widths: Width of the core of the path
        """
        if main_layer is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined."
                " Therefore the layer must be defined in calls"
            )
        extrude_path_dynamic(
            target=c, layer=main_layer, path=path, widths=widths, enclosure=self
        )

    def model_copy(
        self, *, update: Mapping[str, Any] | None = {"name": None}, deep: bool = False
    ) -> LayerEnclosure:
        return super().model_copy(update=update, deep=deep)


class LayerEnclosureSpec(TypedDict):
    main_layer: kdb.LayerInfo
    name: NotRequired[str | None]
    sections: NotRequired[
        list[tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]]
    ]
    dsections: NotRequired[
        list[tuple[kdb.LayerInfo, float] | tuple[kdb.LayerInfo, float, float]]
    ]


class LayerEnclosureCollection(BaseModel):
    """Collection of LayerEnclosures."""

    enclosures: list[LayerEnclosure]

    def __hash__(self) -> int:
        return hash(tuple(self.enclosures))

    def __getitem__(self, key: str | int) -> LayerEnclosure:
        """Retrieve enclosure by main layer."""
        try:
            return next(filter(lambda enc: enc.main_layer == key, self.enclosures))
        except StopIteration as e:
            raise KeyError(f"Unknown key {key}") from e


class KCellLayerEnclosures(BaseModel):
    """Collection of LayerEnclosures."""

    enclosures: list[LayerEnclosure]

    def __hash__(self) -> int:
        return hash(tuple(self.enclosures))

    @field_validator("enclosures")
    @classmethod
    def enclosures_must_have_main_layer(
        cls, v: list[LayerEnclosure]
    ) -> list[LayerEnclosure]:
        """The PDK Enclosure must have main layers defined for each Enclosure.

        The PDK Enclosure uses this to automatically apply enclosures.
        """
        for le in v:
            assert le.main_layer is not None, (
                "Enclosure for PDKEnclosure must have a main layer defined"
            )
        return v

    def __getitem__(self, key: str | int) -> LayerEnclosure:
        """Retrieve enclosure by main layer."""
        try:
            return next(filter(lambda enc: enc.main_layer == key, self.enclosures))
        except StopIteration as e:
            raise KeyError(f"Unknown key {key}") from e

    def get_enclosure(
        self,
        enclosure: str | LayerEnclosure | LayerEnclosureSpec,
    ) -> LayerEnclosure:
        if isinstance(enclosure, str):
            return self[enclosure]
        if isinstance(enclosure, dict) and enclosure.get("dsections") is None:
            enclosure = LayerEnclosure(
                sections=enclosure.get("sections", []),
                name=enclosure.get("name"),
                main_layer=enclosure["main_layer"],
            )

        if enclosure not in self.enclosures:
            self.enclosures.append(enclosure)  # type: ignore[arg-type]
        return enclosure  # type: ignore[return-value]


class RegionOperator(kdb.TileOutputReceiver):
    """Region collector. Just getst the tile and inserts it into the target cell."""

    def __init__(self, cell: KCell, layer: kdb.LayerInfo) -> None:
        """Initialization.

        Args:
            cell: Target cell.
            layer: Target layer.
        """
        self.kcell = cell
        self.layer = layer
        self.region = kdb.Region()

    def put(
        self,
        ix: int,
        iy: int,
        tile: kdb.Box,
        region: kdb.Region,
        dbu: float,
        clip: bool,
    ) -> None:
        """Tiling Processor output call.

        Args:
            ix: x-axis index of tile.
            iy: y_axis index of tile.
            tile: The bounding box of the tile.
            region: The target object of the `klayout.db.TilingProcessor`
            dbu: dbu used by the processor.
            clip: Whether the target was clipped to the tile or not.
        """
        self.region.insert(region)

    @overload
    def insert(self) -> None: ...

    @overload
    def insert(self, port_holes: kdb.Region) -> None: ...

    def insert(
        self,
        port_holes: kdb.Region | None = None,
    ) -> None:
        """Insert the finished region into the cell.

        Args:
            port_holes: Carve out holes around the ports.
        """
        if port_holes:
            self.region -= port_holes
        self.kcell.shapes(self.layer).insert(self.region)


class RegionTilesOperator(kdb.TileOutputReceiver):
    """Region collector. Just getst the tile and inserts it into the target cell.

    As it can be used multiple times for the same tile, it needs to merge when
    inserting.
    """

    def __init__(
        self,
        cell: KCell,
        layers: list[kdb.LayerInfo],
    ) -> None:
        """Initialization.

        Args:
            cell: Target cell.
            layers: Target layers.
        """
        self.kcell = cell
        self.layers = layers
        self.merged_region: kdb.Region = kdb.Region()
        self.merged = False
        self.regions: dict[int, dict[int, kdb.Region]] = defaultdict(
            lambda: defaultdict(kdb.Region)
        )

    def put(
        self,
        ix: int,
        iy: int,
        tile: kdb.Box,
        region: kdb.Region,
        dbu: float,
        clip: bool,
    ) -> None:
        """Tiling Processor output call.

        Args:
            ix: x-axis index of tile.
            iy: y_axis index of tile.
            tile: The bounding box of the tile.
            region: The target object of the `klayout.db.TilingProcessor`
            dbu: dbu used by the processor.
            clip: Whether the target was clipped to the tile or not.
        """
        self.regions[ix][iy].insert(region)

    def merge_region(self) -> None:
        """Create one region from the individual tiles."""
        for dicts in self.regions.values():
            for reg in dicts.values():
                self.merged_region.insert(reg)

    @overload
    def insert(self) -> None: ...

    @overload
    def insert(self, port_hole_map: dict[kdb.LayerInfo, kdb.Region]) -> None: ...

    def insert(
        self,
        port_hole_map: dict[kdb.LayerInfo, kdb.Region] | None = None,
    ) -> None:
        """Insert the finished region into the cell.

        Args:
            port_hole_map: Carve out holes around the ports.
        """
        if not self.merged:
            self.merge_region()

        if port_hole_map:
            for layer in self.layers:
                self.merged_region -= port_hole_map[layer]
            self.kcell.shapes(layer).insert(self.merged_region)
        else:
            for layer in self.layers:
                self.kcell.shapes(layer).insert(self.merged_region)


@lru_cache(None)
def port_hole(port_width: int, section_width: int) -> kdb.Box:
    w_h = port_width // 2 + section_width
    return kdb.Box(0, -w_h, w_h, w_h)


class KCellEnclosure(BaseModel):
    """Collection of [enclosures][kfactory.enclosure.LayerEnclosure] for cells."""

    enclosures: LayerEnclosureCollection

    def __init__(self, enclosures: Iterable[LayerEnclosure]) -> None:
        """Init. Allow usage of an iterable object instead of a collection."""
        super().__init__(
            enclosures=LayerEnclosureCollection(enclosures=list(enclosures))
        )

    def __hash__(self) -> int:
        """Hash of the KCellEnclosure."""
        return hash(tuple(self.enclosures.enclosures))

    def minkowski_region(
        self,
        r: kdb.Region,
        d: int | None,
        shape: Callable[[int], list[kdb.Point] | kdb.Box | kdb.Edge | kdb.Polygon],
    ) -> kdb.Region:
        """Calculaste a region from a minkowski sum.

        If the distance is negative, the function will take the inverse region and apply
        the minkowski and take the inverse again.

        Args:
            r: Target region.
            d: Distance to pass to the shape. Can be any integer. [dbu]
            shape: Function returning a shape for the minkowski region.
        """
        if d is None:
            return kdb.Region()
        if d == 0:
            return r.dup()
        if d > 0:
            return r.minkowski_sum(shape(d))
        shape_ = shape(abs(d))
        if isinstance(shape_, list):
            box_shape = kdb.Polygon(shape_)
            bbox_maxsize = max(
                box_shape.bbox().width(),
                box_shape.bbox().height(),
            )
        else:
            bbox_maxsize = max(
                shape_.bbox().width(),
                shape_.bbox().height(),
            )
        bbox_r = kdb.Region(r.bbox().enlarged(bbox_maxsize))
        return r - (bbox_r - r).minkowski_sum(shape_)

    def apply_minkowski_enc(
        self,
        c: KCell,
        direction: Direction = Direction.BOTH,
    ) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            direction: X/Y or both directions, see [kfactory.enclosure.DIRECTION].
                Uses a box if both directions are selected.
        """
        match direction:
            case Direction.BOTH:

                def box(d: int) -> kdb.Box:
                    return kdb.Box(-d, -d, d, d)

                self.apply_minkowski_custom(c, shape=box)

            case Direction.Y:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(0, -d, 0, d)

                self.apply_minkowski_custom(c, shape=edge)

            case Direction.X:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(-d, 0, d, 0)

                self.apply_minkowski_custom(c, shape=edge)

            case _:
                raise ValueError("Undefined direction")

    def apply_minkowski_y(self, c: KCell) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
        """
        return self.apply_minkowski_enc(c, direction=Direction.Y)

    def apply_minkowski_x(self, c: KCell) -> None:
        """Apply an enclosure with a vector in x-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
        """
        return self.apply_minkowski_enc(c, direction=Direction.X)

    def apply_minkowski_custom(
        self,
        c: KCell,
        shape: Callable[[int], kdb.Edge | kdb.Polygon | kdb.Box],
    ) -> None:
        """Apply an enclosure with a custom shape.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            shape: A function that will return a shape which takes one argument
                the size of the section in dbu.
            shape: Reference to use as a base for the enclosure.
        """
        regions = {}
        for enc in self.enclosures.enclosures:
            main_layer = c.kcl.layer(enc.main_layer)
            if not c.bbox(main_layer).empty():
                rsi = c.begin_shapes_rec(main_layer)
                r = kdb.Region(rsi)
                for layer, layersec in enc.layer_sections.items():
                    if layer not in regions:
                        reg = kdb.Region()
                        regions[layer] = reg
                    else:
                        reg = regions[layer]
                    for section in layersec.sections:
                        reg += self.minkowski_region(
                            r, section.d_max, shape
                        ) - self.minkowski_region(r, section.d_min, shape)

                        reg.merge()

        for layer, region in regions.items():
            c.shapes(c.kcl.layer(layer)).insert(region)

    def apply_minkowski_tiled(
        self,
        c: KCell,
        tile_size: float | None = None,
        n_pts: int = 64,
        n_threads: int | None = None,
        carve_out_ports: bool = True,
    ) -> None:
        """Minkowski regions with tiling processor.

        Useful if the target is a big or complicated enclosure. Will split target ref
        into tiles and calculate them in parallel. Uses a circle as a shape for the
        minkowski sum.

        Args:
            c: Target KCell to apply the enclosures into.
            tile_size: Tile size. This should be in the order off 10+ maximum size
                of the maximum size of sections. [um]
                If None is set, the minimum size is set to 10xmax(d_max) of all sections
                or 200um whichever is bigger.
            n_pts: Number of points in the circle. < 3 will create a triangle. 4 a
                diamond, etc.
            n_threads: Number o threads to use. By default (`None`) it will use as many
                threads as are set to the process (usually all cores of the machine).
            carve_out_ports: Carves out a box of port_width +
        """
        tp = kdb.TilingProcessor()
        tp.frame = c.dbbox()  # type: ignore[misc, assignment]
        tp.dbu = c.kcl.dbu
        tp.threads = n_threads or config.n_threads
        inputs: set[str] = set()
        port_hole_map: dict[kdb.LayerInfo, kdb.Region] = defaultdict(kdb.Region)
        ports_by_layer: dict[kdb.LayerInfo, list[Port]] = defaultdict(list)
        for port in c.ports:
            ports_by_layer[c.kcl.layer(c.kcl.get_info(port.layer))].append(port)

        maxsize = 0
        for enc in self.enclosures.enclosures:
            assert enc.main_layer is not None
            main_layer = c.kcl.layer(enc.main_layer)
            for layer, layersection in enc.layer_sections.items():
                li = c.kcl.layer(layer)
                size = layersection.sections[-1].d_max
                maxsize = max(maxsize, size)

                for port in ports_by_layer[main_layer]:
                    if port._base.trans:
                        port_hole_map[li].insert(
                            port_hole(port.width, size).transformed(port.trans)
                        )
                    else:
                        port_hole_map[li].insert(
                            port_hole(port.width, size).transformed(
                                kdb.ICplxTrans(port.dcplx_trans, port.kcl.dbu)
                            )
                        )

        min_tile_size_rec = 10 * maxsize * tp.dbu

        if tile_size is None:
            tile_size = max(min_tile_size_rec * 2, 200)

        if float(tile_size) <= min_tile_size_rec:
            logger.warning(
                "Tile size should be larger than the maximum of "
                "the enclosures (recommendation: {} / {})",
                tile_size,
                min_tile_size_rec,
            )
        tp.tile_border(maxsize * tp.dbu, maxsize * tp.dbu)
        tp.tile_size(tile_size, tile_size)
        layer_regiontilesoperators: dict[
            tuple[int, LayerSection], RegionTilesOperator
        ] = {}

        logger.debug("Starting KCellEnclosure on {}", c.kcl.future_cell_name or c.name)

        n_enc = len(self.enclosures.enclosures)

        for i, enc in enumerate(self.enclosures.enclosures):
            assert enc.main_layer is not None
            if not c.bbox(c.kcl.layer(enc.main_layer)).empty():
                main_layer = c.kcl.layer(enc.main_layer)
                inp = f"main_layer_{main_layer}"
                if enc.main_layer not in inputs:
                    tp.input(
                        inp,
                        c.kcl.layout,
                        c.cell_index(),
                        main_layer,
                    )
                    inputs.add(main_layer)
                    logger.debug("Created input {}", inp)

                for layer, layer_section in enc.layer_sections.items():
                    li = c.kcl.layer(layer)
                    if (main_layer, layer_section) in layer_regiontilesoperators:
                        layer_regiontilesoperators[
                            main_layer, layer_section
                        ].layers.append(li)
                    else:
                        out = f"target_{li}"
                        operator = RegionTilesOperator(cell=c, layers=[li])
                        layer_regiontilesoperators[main_layer, layer_section] = operator
                        tp.output(out, operator)
                        logger.debug("Created output {}", out)

                    for section in reversed(layer_section.sections):
                        queue_str = (
                            "var max_shape = Polygon.ellipse("
                            f"Box.new({section.d_max * 2},{section.d_max * 2}),"
                            f" {n_pts});"
                            f"var tile_reg = _tile & _frame.sized({maxsize});"
                        )
                        match section.d_max:
                            case d if d > 0:
                                max_region = (
                                    "var max_reg = "
                                    f"{inp}.minkowski_sum(max_shape).merged();"
                                )
                            case d if d < 0:
                                max_region = (
                                    f"var max_reg = tile_reg - (tile_reg - {inp});"
                                )
                            case 0:
                                max_region = f"var max_reg = {inp} & tile_reg;"
                        queue_str += max_region
                        if section.d_min is not None:
                            queue_str += (
                                "var min_shape = Polygon.ellipse("
                                f"Box.new({section.d_min * 2},{section.d_min * 2}),"
                                " 64);"
                            )
                            match section.d_min:
                                case d if d > 0:
                                    min_region = (
                                        f"var min_reg = {inp}.minkowski_sum(min_shape);"
                                    )
                                case d if d < 0:
                                    min_region = (
                                        "var min_reg = tile_reg - (tile_reg - "
                                        f"{inp}).minkowski_sum(min_shape);"
                                    )
                                case 0:
                                    min_region = f"var min_reg = {inp} & tile_reg;"
                            queue_str += min_region
                            queue_str += (
                                f"_output({out},(max_reg - min_reg) & _tile, true);"
                            )
                        else:
                            queue_str += f"_output({out}, max_reg & _tile, true);"

                        logger.debug(
                            "{}/{}: Queuing string for {} on layer {}: '{}'",
                            i + 1,
                            n_enc,
                            c.kcl.future_cell_name or c.name,
                            layer,
                            queue_str,
                        )
                        tp.queue(queue_str)

        c.kcl.start_changes()
        logger.debug(
            "Starting enclosure {}",
            c.kcl.future_cell_name or c.name,
            enc.name,
        )
        tp.execute(f"Minkowski {c.name}")
        c.kcl.end_changes()
        logger.debug("Finished enclosure {}", enc.name)

        if carve_out_ports:
            for operator in layer_regiontilesoperators.values():
                # for layer in operator.layers:
                operator.insert(port_hole_map=port_hole_map)
        else:
            for operator in layer_regiontilesoperators.values():
                operator.insert()
        logger.debug("Finished KCellEnclosure on {}", c.kcl.future_cell_name or c.name)


class LayerEnclosureModel(RootModel[dict[str, LayerEnclosure]]):
    """PDK access model for LayerEnclsoures."""

    root: dict[str, LayerEnclosure] = Field(default_factory=dict)

    def __getitem__(self, __key: str, /) -> LayerEnclosure:
        """Retrieve element by string key."""
        return self.root[__key]

    def __getattr__(self, __key: str, /) -> LayerEnclosure:
        """Retrieve attribute by key."""
        return self.root[__key]

    def __setattr__(self, __key: str, /, __val: LayerEnclosure) -> None:
        """Add a new LayerEnclosure."""
        self.root[__key] = __val

    def __setitem__(self, __key: str, /, __val: LayerEnclosure) -> None:
        """Add a new LayerEnclosure."""
        self.root[__key] = __val

    def get_enclosure(
        self,
        enclosure: str | LayerEnclosure | LayerEnclosureSpec,
        kcl: KCLayout,
    ) -> LayerEnclosure:
        if isinstance(enclosure, str):
            return self[enclosure]
        if isinstance(enclosure, dict):
            if "dsections" in enclosure:
                enclosure = LayerEnclosure(
                    dsections=enclosure.get("dsections", []),
                    name=enclosure.get("name"),
                    main_layer=enclosure["main_layer"],
                    kcl=kcl,
                )
            else:
                enclosure = LayerEnclosure(
                    sections=enclosure.get("sections", []),
                    name=enclosure.get("name"),
                    main_layer=enclosure["main_layer"],
                    kcl=kcl,
                )

        if enclosure.name not in self.root:
            self.root[enclosure.name] = enclosure
            return enclosure
        return self.root[enclosure.name]


def _add_section(
    layer_sections: dict[kdb.LayerInfo, LayerSection],
    layer: kdb.LayerInfo,
    section: Section,
) -> None:
    """Add a new section to the the enclosure.

    Args:
        layer: Target layer.
        sec: New section to add.
    """
    if layer in layer_sections:
        layer_sections[layer].add_section(section)
    else:
        layer_sections[layer] = LayerSection(sections=[section])


LayerEnclosureModel.model_rebuild()
LayerSection.model_rebuild()
LayerEnclosure.model_rebuild()
KCellEnclosure.model_rebuild()
