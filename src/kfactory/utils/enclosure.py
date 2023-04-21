"""Enclosure module.

Enclosures allow to calculate slab/excludes and similar concepts to an arbitrary
shape located on a main_layer or reference layer or region.
"""

import os
from collections.abc import Callable, Sequence
from enum import IntEnum
from hashlib import sha1
from typing import Any, Optional, TypeGuard

import numpy as np
from pydantic import BaseModel, Field, PrivateAttr

from .. import kdb
from ..config import logger
from ..kcell import KCell, LayerEnum

__all__ = [
    "Enclosure",
    "extrude_path",
    "extrude_path_points",
    "extrude_path_dynamic",
    "extrude_path_dynamic_points",
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


def is_callable_widths(
    widths: Callable[[float], float] | list[float]
) -> TypeGuard[Callable[[float], float]]:
    """Determines whether a width object is callable or a list."""
    return callable(widths)


def path_pts_to_polygon(
    pts_top: list[kdb.DPoint], pts_bot: list[kdb.DPoint]
) -> kdb.DPolygon:
    """Convert a list of points to a polygon."""
    pts_bot.reverse()
    return kdb.DPolygon(pts_top + pts_bot)


def _is_Region(r: object) -> TypeGuard[kdb.Region]:
    return isinstance(r, kdb.Region)


def _is_int(r: object) -> TypeGuard[int]:
    return isinstance(r, int)


def _is_callable(r: object) -> TypeGuard[Callable[[float], float]]:
    return callable(r)


def clean_points(points: list[kdb.Point]) -> list[kdb.Point]:
    """Remove useless points from a manhattan type of list.

    This will remove the middle points that are on a straight line.
    """
    if len(points) < 2:
        return points
    if len(points) == 2:
        return points if points[1] != points[0] else points[:1]
    p_p = points[0]
    p = points[1]

    del_points = []

    for i, p_n in enumerate(points[2:], 2):
        v2 = p_n - p
        v1 = p - p_p
        if (
            (np.sign(v1.x) == np.sign(v2.x)) and (np.sign(v1.y) == np.sign(v2.y))
        ) or v2.abs() == 0:
            del_points.append(i - 1)
        p_p = p
        p = p_n

    for i in reversed(del_points):
        del points[i]

    return points


def extrude_path_points(
    path: list[kdb.DPoint],
    width: float,
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """Extrude a path from a list of points and a static width.

    Args:
        path: list of floating-points points
        width: width in µm
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
    layer: LayerEnum | int,
    path: list[kdb.DPoint],
    width: float,
    enclosure: Optional["Enclosure"] = None,
    start_angle: float | None = None,
    end_angle: float | None = None,
) -> None:
    """Extrude a path from a list of points and a static width.

    Args:
        target: the cell where to insert the shapes to (and get the database unit from)
        layer: the main layer that should be extruded
        path: list of floating-points points
        width: width in µm
        enclosure: optoinal enclosure object, specifying necessary
            layers.this will extrude around the `layer`
        start_angle: optionally specify a custom starting angle if `None`
            will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be
            autocalculated from the last two elements
    """
    layer_list = {layer: LayerSection(sections=[Section(d_max=0)])}
    if enclosure is not None:
        if layer not in enclosure.layer_sections:
            layer_list |= enclosure.layer_sections
        else:
            layer_list[layer].sections.copy()
            layer_list = enclosure.layer_sections.copy()
            for section in layer_list[layer].sections:
                layer_list[layer].add_section(section)

    for layer, layer_sec in layer_list.items():
        reg = kdb.Region()
        for section in layer_sec.sections:
            _r = kdb.Region(
                path_pts_to_polygon(
                    *extrude_path_points(
                        path,
                        width + 2 * section.d_max * target.klib.dbu,
                        start_angle,
                        end_angle,
                    )
                ).to_itype(target.klib.dbu)
            )
            if section.d_min is not None:
                _r -= kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_points(
                            path,
                            width + 2 * section.d_min * target.klib.dbu,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
            reg.insert(_r)
        target.shapes(layer).insert(reg.merge())


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
        length = sum(((p2 - p1).abs() for p2, p1 in zip(path[:-1], path[1:])))
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
        for point, w in zip(path[2:], widths[1:-1]):
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
    layer: LayerEnum | int,
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    enclosure: Optional["Enclosure"] = None,
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
        enclosure: optoinal enclosure object, specifying necessary layers.this will
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
        for layer, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:

                def w_max(x: float) -> float:
                    return (
                        widths(x)  # type: ignore[operator]
                        + 2 * section.d_max * target.klib.dbu
                    )

                _r = kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_dynamic_points(
                            path,
                            w_max,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
                if section.d_min is not None:

                    def w_min(x: float) -> float:
                        return (
                            widths(x)  # type: ignore[operator]
                            + 2  # type: ignore[operator]
                            * section.d_min
                            * target.klib.dbu
                        )

                    _r -= kdb.Region(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                w_min,
                                start_angle,
                                end_angle,
                            )
                        ).to_itype(target.klib.dbu)
                    )
                reg.insert(_r)
            target.shapes(layer).insert(reg.merge())

    else:
        for layer, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:
                max_widths = [
                    w + 2 * section.d_max * target.klib.dbu
                    for w in widths  # type: ignore[union-attr]
                ]
                _r = kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_dynamic_points(
                            path,
                            max_widths,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
                if section.d_min is not None:
                    min_widths = [
                        w + 2 * section.d_min * target.klib.dbu
                        for w in widths  # type: ignore[union-attr]
                    ]
                    _r -= kdb.Region(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                min_widths,
                                start_angle,
                                end_angle,
                            )
                        ).to_itype(target.klib.dbu)
                    )
                reg.insert(_r)
            target.shapes(layer).insert(reg.merge())


class Section(BaseModel):
    """Section of an Enclosure.

    Visualization::

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

    sections: list[Section] = Field(default=[])

    def add_section(self, sec: Section) -> None:
        """Add a new section.

        Checks for overlaps after.
        """
        if not self.sections:
            self.sections.append(sec)
        else:
            i = 0
            if sec.d_min is not None:
                while i < len(self.sections) and sec.d_min > self.sections[i].d_max:
                    i += 1
                while (
                    i < len(self.sections)
                    and sec.d_max >= self.sections[i].d_min  # type: ignore[operator]
                ):
                    sec.d_max = max(self.sections[i].d_max, sec.d_max)
                    sec.d_min = min(
                        self.sections[i].d_min, sec.d_min  # type: ignore[type-var]
                    )
                    self.sections.pop(i)
                    if i == len(self.sections):
                        break
            self.sections.insert(i, sec)

    def __hash__(self) -> int:
        """Unique hash of LayerSection."""
        return hash(tuple((s.d_min, s.d_max) for s in self.sections))


class Enclosure(BaseModel):
    """Definitions for calculation of enclosing (or smaller) shapes of a reference.

    Attributes:
        layer_sections: Mapping of layers to their :py:class;`LayerSection`

    """

    layer_sections: dict[LayerEnum | int, LayerSection]
    _name: str | None = PrivateAttr(default=None)
    warn: bool = True

    main_layer: LayerEnum | int | None

    yaml_tag: str = "!Enclosure"

    class Config:
        """pydantic config."""

        validate_assignment = True

    def __init__(
        self,
        sections: Sequence[
            tuple[LayerEnum | int, int] | tuple[LayerEnum | int, int, int]
        ] = [],
        name: str | None = None,
        warn: bool = True,
        main_layer: LayerEnum | int | None = None,
    ):
        """Constructor of new enclosure."""
        super().__init__(
            warn=warn,
            layer_sections={},
            main_layer=main_layer,
        )

        self._name = name

        self.layer_sections = {}

        for sec in sorted(sections, key=lambda sec: (sec[0], sec[1])):
            if sec[0] in self.layer_sections:
                ls = self.layer_sections[sec[0]]
            else:
                ls = LayerSection()
                self.layer_sections[sec[0]] = ls
            ls.add_section(Section(d_max=sec[1])) if len(sec) < 3 else ls.add_section(
                Section(d_max=sec[2], d_min=sec[1])  # type:ignore[misc]
            )

    def __hash__(self) -> int:  # make hashable BaseModel subclass
        """Calculate a unique hash of the enclosure."""
        return hash(
            (str(self), self.main_layer, tuple(list(self.layer_sections.items())))
        )

    def __add__(self, other: "Enclosure") -> "Enclosure":
        """Returns the merged enclosure of two enclosures."""
        enc = Enclosure()

        for layer, secs in self.layer_sections.items():
            for sec in secs.sections:
                enc.add_section(layer, sec)

        for layer, secs in other.layer_sections.items():
            for sec in secs.sections:
                enc.add_section(layer, sec)

        return enc

    def __iadd__(self, other: "Enclosure") -> "Enclosure":
        """Allows merging another enclosure into this one."""
        for layer, secs in other.layer_sections.items():
            for sec in secs.sections:
                self.add_section(layer, sec)
        return self

    def add_section(self, layer: LayerEnum | int, sec: Section) -> None:
        """Add a new section to the the enclosure.

        Args:
            layer: Target layer.
            sec: New section to add.
        """
        d = self.layer_sections

        if layer in self.layer_sections:
            d[layer].add_section(sec)
        else:
            d[layer] = LayerSection(sections=[sec])

        self.layer_sections = d  # trick pydantic to validate

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
        elif d == 0:
            return r.dup()
        elif d > 0:
            return r.minkowski_sum(shape(d))
        else:
            _shape = shape(abs(d))
            if isinstance(_shape, list):
                box_shape = kdb.Polygon(_shape)
                bbox_maxsize = max(
                    box_shape.bbox().width(),
                    box_shape.bbox().height(),
                )
            else:
                bbox_maxsize = max(
                    _shape.bbox().width(),
                    _shape.bbox().height(),
                )
            bbox_r = kdb.Region(r.bbox().enlarged(bbox_maxsize))
            return r - (bbox_r - r).minkowski_sum(_shape)

    def apply_minkowski_enc(
        self,
        c: KCell,
        ref: int | kdb.Region | None,  # layer index or the region
        direction: Direction = Direction.BOTH,
    ) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            ref: Reference to use as a base for the enclosure.
            direction: X/Y or both directions, see :py:class:~`DIRECTION`.
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

    def apply_minkowski_y(self, c: KCell, ref: int | kdb.Region | None = None) -> None:
        """Apply an enclosure with a vector in y-direction.

        This can be used for tapers/
        waveguides or similar that are straight.

        Args:
            c: Cell to apply the enclosure to.
            ref: Reference to use as a base for the enclosure.
        """
        return self.apply_minkowski_enc(c, ref=ref, direction=Direction.Y)

    def apply_minkowski_x(self, c: KCell, ref: int | kdb.Region | None) -> None:
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
        ref: int | kdb.Region | None = None,
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
        r = kdb.Region(c.begin_shapes_rec(ref)) if isinstance(ref, int) else ref.dup()
        r.merge()

        for layer, layersec in reversed(self.layer_sections.items()):
            for section in layersec.sections:
                c.shapes(layer).insert(
                    self.minkowski_region(r, section.d_max, shape)
                    - self.minkowski_region(r, section.d_min, shape)
                )

    def apply_minkowski_tiled(
        self,
        c: KCell,
        ref: int | kdb.Region | None = None,
        tile_size: float | None = None,
        n_pts: int = 64,
        n_threads: int | None = None,
    ) -> None:
        """Minkowski regions with tiling processor.

        Useful if the target is a big or complicated enclosure. Will split target ref
        into tiles and calculate them in parallel. Uses a circle as a shape for the
        minkowski sum.

        Args:
            c: Target KCell to apply the enclosures into.
            ref: The reference shapes to apply the enclosures to.
                Can be a layer or a region. If `None`, it will trey to use the
                :py:attr:`main_layer`
            tile_size: Tile size. This should be in the order off 10+ maximum size
                of the maximum size of sections.
            n_pts: Number of points in the circle. < 3 will create a triangle. 4 a
                diamond, etc.
            n_threads: Number o threads to use. By default (`None`) it will use as many
                threads as are set to the process (usually all cores of the machine).
        """
        if ref is None:
            ref = self.main_layer

            if ref is None:
                raise ValueError(
                    "The enclosure doesn't have  a reference `main_layer` defined."
                    " Therefore the layer must be defined in calls"
                )
        tp = kdb.TilingProcessor()
        tp.frame = c.dbbox()  # type: ignore[misc]
        tp.dbu = c.klib.dbu
        tp.threads = n_threads or len(os.sched_getaffinity(0))
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
        if isinstance(ref, int):
            tp.input("main_layer", c.klib, c.cell_index(), ref)
        else:
            tp.input("main_layer", ref)

        operators = []

        for layer, sections in self.layer_sections.items():
            operator = RegionOperator(cell=c, layer=layer)
            tp.output(f"target_{layer}", operator)
            for i, section in enumerate(reversed(sections.sections)):
                queue_str = f"var tile_reg = (_tile & _frame).sized({maxsize});"
                queue_str += (
                    "var max_shape = Polygon.ellipse("
                    f"Box.new({section.d_max*2},{section.d_max*2}), {n_pts});"
                )
                match section.d_max:
                    case d if d > 0:
                        max_region = (
                            "var max_reg = "
                            "main_layer.minkowski_sum(max_shape).merged();"
                        )
                    case d if d < 0:
                        max_region = (
                            "var max_reg = tile_reg - " "(tile_reg - main_layer);"
                        )
                    case 0:
                        max_region = "var max_reg = main_layer & tile_reg;"
                queue_str += max_region
                if section.d_min:
                    queue_str += (
                        "var min_shape = Polygon.ellipse("
                        f"Box.new({section.d_min*2},{section.d_min*2}), 64);"
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
                        f"_output(target_{layer}," "(max_reg - min_reg)& _tile, true);"
                    )
                else:
                    queue_str += f"_output(target_{layer},max_reg & _tile, true);"

                tp.queue(queue_str)
                logger.debug(
                    "String queued for {} on layer {}: {}", c.name, layer, queue_str
                )

            operators.append((layer, operator))

        c.klib.start_changes()
        logger.info("Starting minkowski on {}", c.name)
        tp.execute(f"Minkowski {c.name}")
        c.klib.end_changes()

        for layer, operator in operators:
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
            for sec in layersec.sections:
                c.shapes(layer).insert(shape(sec.d_max, sec.d_min))

    def apply_bbox(self, c: KCell, ref: int | kdb.Region | None = None) -> None:
        """Apply an enclosure based on a bounding box.

        Args:
            c: Target cell.
            ref: Reference layer or region (the bounding box). If `None` use
                :py:attr:~`main_layer` if defined, else throw an error.
        """
        if ref is None:
            ref = self.main_layer

            if ref is None:
                raise ValueError(
                    "The enclosure doesn't have  a reference `main_layer` defined."
                    " Therefore the layer must be defined in calls"
                )

        if _is_int(ref):
            _ref = c.bbox_per_layer(ref)
        elif _is_Region(ref):
            _ref = ref.bbox()

        def bbox_reg(d_max: int, d_min: int | None = None) -> kdb.Region:
            reg_max = kdb.Region(_ref)
            reg_max.size(d_max)
            if d_min is None:
                return reg_max
            reg_min = kdb.Region(_ref)
            reg_min.size(d_min)
            return reg_max - reg_min

        self.apply_custom(c, bbox_reg)

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Get YAML representation of the enclosure."""
        d = dict(node.enclosures)
        return representer.represent_mapping(cls.yaml_tag, d)

    def __str__(self) -> str:
        """String of enclosure. Use :py:attr:~`name`.

        Use a hash of the sections and main_layer if the name is `None`.
        """
        if self._name is not None:
            return self._name
        list_to_hash: Any = [
            self.main_layer,
        ]
        for layer, layer_section in self.layer_sections.items():
            list_to_hash.append([str(layer), str(layer_section.sections)])
        return sha1(str(list_to_hash).encode("UTF-8")).hexdigest()[-8:]

    def extrude_path(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: int | LayerEnum | None,
        width: float,
    ) -> None:
        """Extrude a path and add it to a main layer.

        Args:
            c: The cell where to insert the path to
            path: Backbone of the path. [um]
            main_layer: Layer index where to put the main part of the path.
            width: Width of the core of the path
        """
        if main_layer is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined."
                " Therefore the layer must be defined in calls"
            )
        extrude_path(target=c, layer=main_layer, path=path, width=width, enclosure=self)

    def extrude_path_dynamic(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: int | LayerEnum | None,
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


class RegionOperator(kdb.TileOutputReceiver):
    """Region collector. Just getst the tile and inserts it into the target cell."""

    def __init__(self, cell: KCell, layer: LayerEnum | int) -> None:
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
            region: The target object of the :py:class:~`klayout.db.TilingProcessor`
            dbu: dbu used by the processor.
            clip: Whether the target was clipped to the tile or not.
        """
        self.region.insert(region)

    def insert(self) -> None:
        """Insert the finished region into the cell."""
        self.kcell.shapes(self.layer).insert(self.region)
