"""Create 1D or 2D (flex) grids in KCells."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from . import kdb
from .instance_group import DInstanceGroup, InstanceGroup
from .kcell import DKCell, KCell

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .instance import DInstance, Instance

__all__ = ["flexgrid", "flexgrid_dbu", "grid", "grid_dbu"]


def grid_dbu(
    target: KCell,
    kcells: Sequence[KCell | None] | Sequence[Sequence[KCell | None]],
    spacing: int | tuple[int, int],
    target_trans: kdb.Trans | None = None,
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
) -> InstanceGroup:
    """Create a grid of instances.

    A grid uses the bounding box of the biggest width and biggest height of any bounding
    boxes inserted into the grid.
    to this bounding box a spacing is applied in x and y.

    ```
                          spacing[0] or spacing
                         ◄─►
      ┌──────────────────┐ ┌────┬─────┬─────┐ ┌────────────────┐ ┌──────────────────┐ ▲
      │                  │ │    │     │     │ │                │ │                  │ │
      │   ┌────┐         │ │    │     │     │ │                │ │      ┌──────┐    │ │
      │   │    │         │ │    │     │     │ │                │ │      │      │    │ │
      │   │    │         │ │    │ big │     │ │    ┌───────┐   │ │      │      │    │ │
      │   │    │         │ │    │ comp│     │ │    │       │   │ │      │      │    │ │
      │   │    │         │ │    │ y   │     │ │    │       │   │ │      │      │    │ │
      │   │    │         │ │    │     │     │ │    │       │   │ │      │     max bbox y
      │   └────┘         │ │    │     │     │ │    │       │   │ │      │      │    │ │
      │                  │ │    │     │     │ │    │       │   │ │      │      │    │ │
      │                  │ │    │     │     │ │    │       │   │ │      └──────┘    │ │
      │                  │ │    │     │     │ │    │       │   │ │                  │ │
      │                  │ │    │     │     │ │    └───────┘   │ │                  │ │
      │                  │ │    │     │     │ │                │ │                  │ │
     ▲└──────────────────┘ └────┴─────┴─────┘ └────────────────┘ └──────────────────┘ ▼
     │spacing[1] or spacing
     ▼┌──────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐
      │                  │ │                │ │                │ │                  │
      │                  │ │                │ │ ┌────┐         │ │  ┌───┐           │
      ├──────────────────┤ │ ┌───────────┐  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │   big comp x     │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      ├──────────────────┤ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ └───────────┘  │ │ └────┘         │ │  └───┘           │
      │                  │ │                │ │                │ │                  │
      └──────────────────┘ └────────────────┘ └────────────────┘ └──────────────────┘

                                                                 ◄──────────────────►
                                                                    max bbox x
    ```

    Args:
        target: Target KCell.
        kcells: Sequence or sequence of sequence of KCells to add to the grid
        spacing: Value or tuple of value (different x/y) for spacing of the grid. [dbu]
        target_trans: Apply a transformation to the whole grid before placing it.
        shape: Respace the input of kcells into an array and fill as many positions
            (first x then y).
        align_x: Align all the instance on the x-coordinate.
        align_y: Align all the instance on the y-coordinate.
        rotation: Apply a rotation to each kcells instance before adding it to the grid.
        mirror: Mirror the instances before placing them in the grid

    """
    if isinstance(spacing, tuple):
        spacing_x, spacing_y = spacing
    else:
        spacing_x = spacing
        spacing_y = spacing

    if target_trans is None:
        target_trans = kdb.Trans()

    insts: list[list[Instance | None]]
    kcell_array: Sequence[Sequence[KCell]]

    if shape is None:
        if isinstance(kcells[0], KCell):  # noqa: SIM108
            kcell_array = [list(kcells)]  # type:ignore[arg-type]
        else:
            kcell_array = kcells  # type: ignore[assignment]

        x0 = 0
        y0 = 0

        insts = [
            [
                target.create_inst(kcell, kdb.Trans(rotation, mirror, 0, 0))
                for kcell in array
            ]
            for array in kcell_array
        ]
        bboxes = [
            [None if inst is None else inst.bbox() for inst in array] for array in insts
        ]
        w = max(
            max(0 if bbox is None else bbox.width() + spacing_x for bbox in box_array)
            for box_array in bboxes
        )
        h = max(
            max(0 if bbox is None else bbox.height() + spacing_y for bbox in box_array)
            for box_array in bboxes
        )
        for array, bbox_array in zip(insts, bboxes, strict=False):
            y0 += h - h // 2
            for bbox, inst in zip(bbox_array, array, strict=False):
                x0 += w - w // 2
                if bbox is not None and inst is not None:
                    match align_x:
                        case "xmin":
                            x = -bbox.left
                        case "xmax":
                            x = -bbox.right
                        case "center":
                            x = -bbox.center().x
                        case _:
                            x = 0
                    match align_y:
                        case "ymin":
                            y = -bbox.bottom
                        case "ymax":
                            y = -bbox.top
                        case "center":
                            y = -bbox.center().y
                        case _:
                            y = 0
                    at = kdb.Trans(x0 + x, y0 + y)

                    inst.transform(target_trans * at)
                x0 += w // 2
            y0 += h // 2
            x0 = 0
        return InstanceGroup(
            [inst for array in insts for inst in array if inst is not None]
        )
    _kcells: Sequence[KCell | None]
    if isinstance(kcells[0], KCell):
        _kcells = cast("Sequence[KCell | None]", kcells)
    else:
        _kcells = [
            kcell
            for array in cast("Sequence[Sequence[KCell | None]]", kcells)
            for kcell in array
        ]

    if len(_kcells) > shape[0] * shape[1]:
        raise ValueError(
            f"Shape container size {shape[0] * shape[1]=!r} must be bigger "
            f"than the number of kcells {len(_kcells)}"
        )

    x0 = 0
    y0 = 0

    _insts = [
        None
        if kcell is None
        else target.create_inst(kcell, kdb.Trans(rotation, mirror, 0, 0))
        for kcell in _kcells
    ]

    insts = []
    for _ in range(shape[0]):
        insts.append([None] * shape[1])

    shape_bboxes = [None if inst is None else inst.bbox() for inst in _insts]
    shape_bboxes_heights = [0 if box is None else box.height() for box in shape_bboxes]
    shape_bboxes_widths = [0 if box is None else box.width() for box in shape_bboxes]
    w = max(shape_bboxes_widths) + spacing_x
    h = max(shape_bboxes_heights) + spacing_y
    for i, (inst, bbox) in enumerate(zip(_insts, shape_bboxes, strict=False)):
        i_x = i % shape[1]
        i_y = i // shape[1]
        insts[i_y][i_x] = inst
        if i_x == 0:
            y0 += h - h // 2
            x0 = 0
        else:
            x0 += w - w // 2

        if bbox is not None and inst is not None:
            match align_x:
                case "xmin":
                    x = -bbox.left
                case "xmax":
                    x = -bbox.right
                case "center":
                    x = -bbox.center().x
                case _:
                    x = 0
            match align_y:
                case "ymin":
                    y = -bbox.bottom
                case "ymax":
                    y = -bbox.top
                case "center":
                    y = -bbox.center().y
                case _:
                    y = 0
            at = kdb.Trans(x0 + x, y0 + y)

            inst.transform(target_trans * at)
        if i_x == shape[1] - 1:
            y0 += h // 2
            x0 = 0
        else:
            x0 += w // 2
    return InstanceGroup(
        [inst for array in insts for inst in array if inst is not None]
    )


def flexgrid_dbu(
    target: KCell,
    kcells: Sequence[KCell | None] | Sequence[Sequence[KCell | None]],
    spacing: int | tuple[int, int],
    target_trans: kdb.Trans | None = None,
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
) -> InstanceGroup:
    """Create a grid of instances.

    A grid uses the bounding box of the biggest width per column and biggest height per
    row of any bounding boxes inserted into the grid.
    To this bounding box a spacing is applied in x and y.

    ```
                         spacing[0] or spacing
                        ◄─►
     ┌──────────────────┐ ┌──┬─────┬──┐ ┌──────────┐ ┌──────────┐▲
     │                  │ │  │     │  │ │          │ │          ││
     │   ┌────┐         │ │  │     │  │ │          │ │   ┌──────┼│
     │   │    │         │ │  │     │  │ │          │ │   │      ││
     │   │    │         │ │  │ big │  │ │  ┌───────┤ │   │      ││
     │   │ ▼  │         │ │  │ comp│  │ │  │       │ │   │      ││
     │   │    │         │ │  │ y   │  │ │  │       │ │   │  ▼   ││
     │   │    │         │ │  │     │  │ │  │  ▼    │ │   │      ││ y[1]
     │   └────┘         │ │  │ ▼   │  │ │  │       │ │   │      ││
     │                  │ │  │     │  │ │  │       │ │   │      ││
     │                  │ │  │     │  │ │  │       │ │   └──────┼│
     │                  │ │  │     │  │ │  │       │ │          ││
     │                  │ │  │     │  │ │  └───────┤ │          ││
     │                  │ │  │     │  │ │          │ │          ││
    ▲└──────────────────┘ └──┴─────┴──┘ └──────────┘ └──────────┘▼
    │spacing[1] or spacing
    ▼┌──────────────────┐ ┌───────────┐ ┌────┬─────┐ ┌───┬──────┐▲
     ├──────────────────┤ ├───────────┤ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │              ▼   │ │           │ │    │     │ │   │      ││
     │   big comp x     │ │           │ │    │     │ │   │      ││
     │                  │ │    ▼      │ │  ▼ │     │ │ ▼ │      ││ y[0]
     ├──────────────────┤ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     └──────────────────┴─┴───────────┴─┴────┼─────┴─┴───┼──────┘►
     ►──────────────────► ►───────────► ►──────────► ►──────────►
             x[0]               x[1]        x[2]         x[3]
    ```

    Args:
        target: Target KCell.
        kcells: Sequence or sequence of sequence of KCells to add to the grid
        spacing: Value or tuple of value (different x/y) for spacing of the grid. [dbu]
        target_trans: Apply a transformation to the whole grid before placing it.
        shape: Respace the input of kcells into an array and fill as many positions
            (first x then y).
        align_x: Align all the instance on the x-coordinate.
        align_y: Align all the instance on the y-coordinate.
        rotation: Apply a rotation to each kcells instance before adding it to the grid.
        mirror: Mirror the instances before placing them in the grid

    """
    if isinstance(spacing, tuple):
        spacing_x, spacing_y = spacing
    else:
        spacing_x = spacing
        spacing_y = spacing

    if target_trans is None:
        target_trans = kdb.Trans()

    insts: list[list[Instance | None]]
    kcell_array: Sequence[Sequence[KCell]]

    if shape is None:
        if isinstance(kcells[0], KCell):
            kcell_array = cast("Sequence[list[KCell]]", [list(kcells)])
        else:
            kcell_array = cast("Sequence[Sequence[KCell]]", kcells)

        x0 = 0
        y0 = 0

        insts = [
            [
                None
                if kcell is None
                else target.create_inst(kcell, kdb.Trans(rotation, mirror, 0, 0))
                for kcell in array
            ]
            for array in kcell_array
        ]
        bboxes = [
            [None if inst is None else inst.bbox() for inst in array] for array in insts
        ]
        xmin: dict[int, int] = {}
        ymin: dict[int, int] = {}
        ymax: dict[int, int] = {}
        xmax: dict[int, int] = {}
        for i_y, (array, box_array) in enumerate(zip(insts, bboxes, strict=False)):
            for i_x, (inst, bbox) in enumerate(zip(array, box_array, strict=False)):
                if inst is not None and bbox is not None:
                    match align_x:
                        case "xmin":
                            x = -bbox.left
                        case "xmax":
                            x = -bbox.right
                        case "center":
                            x = -bbox.center().x
                        case _:
                            x = 0
                    match align_y:
                        case "ymin":
                            y = -bbox.bottom
                        case "ymax":
                            y = -bbox.top
                        case "center":
                            y = -bbox.center().y
                        case _:
                            y = 0
                    at = kdb.Trans(x, y)
                    inst.trans = at * inst.trans
                    bbox_ = inst.bbox()
                    xmin[i_x] = min(xmin.get(i_x) or bbox_.left, bbox_.left - spacing_x)
                    xmax[i_x] = max(xmax.get(i_x) or bbox_.right, bbox_.right)
                    ymin[i_y] = min(
                        ymin.get(i_y) or bbox_.bottom, bbox_.bottom - spacing_y
                    )
                    ymax[i_y] = max(ymax.get(i_y) or bbox_.top, bbox_.top)

        for i_y, (array, bbox_array) in enumerate(zip(insts, bboxes, strict=False)):
            y0 -= ymin.get(i_y, 0)
            for i_x, (bbox, inst) in enumerate(zip(bbox_array, array, strict=False)):
                x0 -= xmin.get(i_x, 0)
                if inst is not None and bbox is not None:
                    at = kdb.Trans(x0, y0)
                    inst.transform(target_trans * at)
                x0 += xmax.get(i_x, 0)
            y0 += ymax.get(i_y, 0)
            x0 = 0
        return InstanceGroup(
            [inst for array in insts for inst in array if inst is not None]
        )
    _kcells: Sequence[KCell | None]
    if isinstance(kcells[0], KCell):
        _kcells = cast("Sequence[KCell | None]", kcells)
    else:
        _kcells = [
            kcell
            for array in cast("Sequence[Sequence[KCell | None]]", kcells)
            for kcell in array
        ]

    if len(_kcells) > shape[0] * shape[1]:
        raise ValueError(
            f"Shape container size {shape[0] * shape[1]=} must be bigger "
            f"than the number of kcells {len(_kcells)}"
        )

    x0 = 0
    y0 = 0

    _insts = [
        None
        if kcell is None
        else target.create_inst(kcell, kdb.Trans(rotation, mirror, 0, 0))
        for kcell in _kcells
    ]

    xmin = {}
    ymin = {}
    ymax = {}
    xmax = {}
    for i, inst in enumerate(_insts):
        i_x = i % shape[1]
        i_y = i // shape[1]

        if inst is not None:
            bbox = inst.bbox()
            match align_x:
                case "xmin":
                    x = -bbox.left
                case "xmax":
                    x = -bbox.right
                case "center":
                    x = -bbox.center().x
                case _:
                    x = 0
            match align_y:
                case "ymin":
                    y = -bbox.bottom
                case "ymax":
                    y = -bbox.top
                case "center":
                    y = -bbox.center().y
                case _:
                    y = 0
            at = kdb.Trans(x, y)
            inst.trans = at * inst.trans
            bbox = inst.bbox()
            xmin[i_x] = min(xmin.get(i_x) or bbox.left, bbox.left - spacing_x)
            xmax[i_x] = max(xmax.get(i_x) or bbox.right, bbox.right)
            ymin[i_y] = min(ymin.get(i_y) or bbox.bottom, bbox.bottom - spacing_y)
            ymax[i_y] = max(ymax.get(i_y) or bbox.top, bbox.top)

    insts = []
    for _ in range(shape[0]):
        insts.append([None] * shape[1])

    for i, inst in enumerate(_insts):
        i_x = i % shape[1]
        i_y = i // shape[1]
        if i_x == 0:
            y0 -= ymin.get(i_y, 0)
            x0 = 0
        else:
            x0 -= xmin.get(i_x, 0)

        if inst is not None:
            at = kdb.Trans(x0, y0)
            inst.transform(target_trans * at)
            insts[i_y][i_x] = inst
        if i_x == shape[1] - 1:
            y0 += ymax.get(i_y, 0)
            x0 = 0
        else:
            x0 += xmax.get(i_x, 0)
    return InstanceGroup(
        [inst for array in insts for inst in array if inst is not None]
    )


def grid(
    target: DKCell,
    kcells: Sequence[DKCell | None] | Sequence[Sequence[DKCell | None]],
    spacing: float | tuple[float, float],
    target_trans: kdb.DCplxTrans | None = None,
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] = "center",
    rotation: float = 0,
    mirror: bool = False,
) -> DInstanceGroup:
    """Create a grid of instances.

    A grid uses the bounding box of the biggest width and biggest height of any bounding
    boxes inserted into the grid.
    to this bounding box a spacing is applied in x and y.

    ```
                          spacing[0] or spacing
                         ◄─►
      ┌──────────────────┐ ┌────┬─────┬─────┐ ┌────────────────┐ ┌──────────────────┐ ▲
      │                  │ │    │     │     │ │                │ │                  │ │
      │   ┌────┐         │ │    │     │     │ │                │ │      ┌──────┐    │ │
      │   │    │         │ │    │     │     │ │                │ │      │      │    │ │
      │   │    │         │ │    │ big │     │ │    ┌───────┐   │ │      │      │    │ │
      │   │    │         │ │    │ comp│     │ │    │       │   │ │      │      │    │ │
      │   │    │         │ │    │ y   │     │ │    │       │   │ │      │      │    │ │
      │   │    │         │ │    │     │     │ │    │       │   │ │      │     max bbox y
      │   └────┘         │ │    │     │     │ │    │       │   │ │      │      │    │ │
      │                  │ │    │     │     │ │    │       │   │ │      │      │    │ │
      │                  │ │    │     │     │ │    │       │   │ │      └──────┘    │ │
      │                  │ │    │     │     │ │    │       │   │ │                  │ │
      │                  │ │    │     │     │ │    └───────┘   │ │                  │ │
      │                  │ │    │     │     │ │                │ │                  │ │
     ▲└──────────────────┘ └────┴─────┴─────┘ └────────────────┘ └──────────────────┘ ▼
     │spacing[1] or spacing
     ▼┌──────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐
      │                  │ │                │ │                │ │                  │
      │                  │ │                │ │ ┌────┐         │ │  ┌───┐           │
      ├──────────────────┤ │ ┌───────────┐  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │   big comp x     │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      ├──────────────────┤ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ │           │  │ │ │    │         │ │  │   │           │
      │                  │ │ └───────────┘  │ │ └────┘         │ │  └───┘           │
      │                  │ │                │ │                │ │                  │
      └──────────────────┘ └────────────────┘ └────────────────┘ └──────────────────┘

                                                                 ◄──────────────────►
                                                                    max bbox x
    ```

    Args:
        target: Target DKCell.
        kcells: Sequence or sequence of sequence of DKCells to add to the grid
        spacing: Value or tuple of value (different x/y) for spacing of the grid. [um]
        target_trans: Apply a transformation to the whole grid before placing it.
        shape: Respace the input of kcells into an array and fill as many positions
            (first x then y).
        align_x: Align all the instance on the x-coordinate.
        align_y: Align all the instance on the y-coordinate.
        rotation: Apply a rotation to each kcells instance before adding it to the grid.
        mirror: Mirror the instances before placing them in the grid

    """
    if isinstance(spacing, tuple):
        spacing_x, spacing_y = spacing
    else:
        spacing_x = spacing
        spacing_y = spacing

    if target_trans is None:
        target_trans = kdb.DCplxTrans()

    insts: list[list[DInstance | None]]
    kcell_array: Sequence[Sequence[DKCell]]

    if shape is None:
        if isinstance(kcells[0], DKCell):  # noqa: SIM108
            kcell_array = [list(kcells)]  # type:ignore[arg-type]
        else:
            kcell_array = kcells  # type: ignore[assignment]

        x0: float = 0
        y0: float = 0

        insts = [
            [
                target.create_inst(kcell, kdb.DCplxTrans(1, rotation, mirror, 0, 0))
                for kcell in array
            ]
            for array in kcell_array
        ]
        bboxes = [
            [None if inst is None else inst.dbbox() for inst in array]
            for array in insts
        ]
        w: float = max(
            max(0 if bbox is None else bbox.width() + spacing_x for bbox in box_array)
            for box_array in bboxes
        )
        h: float = max(
            max(0 if bbox is None else bbox.height() + spacing_y for bbox in box_array)
            for box_array in bboxes
        )
        for array, bbox_array in zip(insts, bboxes, strict=False):
            y0 += h - h / 2
            for bbox, inst in zip(bbox_array, array, strict=False):
                x0 += w - w / 2
                if bbox is not None and inst is not None:
                    match align_x:
                        case "xmin":
                            x = -bbox.left
                        case "xmax":
                            x = -bbox.right
                        case "center":
                            x = -bbox.center().x
                        case _:
                            x = 0
                    match align_y:
                        case "ymin":
                            y = -bbox.bottom
                        case "ymax":
                            y = -bbox.top
                        case "center":
                            y = -bbox.center().y
                        case _:
                            y = 0
                    at = kdb.DCplxTrans(x0 + x, y0 + y)

                    inst.transform(target_trans * at)
                x0 += w / 2
            y0 += h / 2
            x0 = 0
        return DInstanceGroup(
            [inst for array in insts for inst in array if inst is not None]
        )
    _kcells: Sequence[DKCell | None]
    if isinstance(kcells[0], DKCell):
        _kcells = cast("Sequence[DKCell | None]", kcells)
    else:
        _kcells = [
            kcell
            for array in cast("Sequence[Sequence[DKCell | None]]", kcells)
            for kcell in array
        ]

    if len(_kcells) > shape[0] * shape[1]:
        raise ValueError(
            f"Shape container size {shape[0] * shape[1]=!r} must be bigger "
            f"than the number of kcells {len(_kcells)}"
        )

    x0 = 0
    y0 = 0

    _insts = [
        None
        if kcell is None
        else target.create_inst(kcell, kdb.DCplxTrans(1, rotation, mirror, 0, 0))
        for kcell in _kcells
    ]

    insts = []
    for _ in range(shape[0]):
        insts.append([None] * shape[1])

    shape_bboxes = [None if inst is None else inst.dbbox() for inst in _insts]
    shape_bboxes_heights = [0 if box is None else box.height() for box in shape_bboxes]
    shape_bboxes_widths = [0 if box is None else box.width() for box in shape_bboxes]
    w = max(shape_bboxes_widths) + spacing_x
    h = max(shape_bboxes_heights) + spacing_y
    for i, (inst, bbox) in enumerate(zip(_insts, shape_bboxes, strict=False)):
        i_x = i % shape[1]
        i_y = i // shape[1]
        insts[i_y][i_x] = inst
        if i_x == 0:
            y0 += h - h / 2
            x0 = 0
        else:
            x0 += w - w / 2

        if bbox is not None and inst is not None:
            match align_x:
                case "xmin":
                    x = -bbox.left
                case "xmax":
                    x = -bbox.right
                case "center":
                    x = -bbox.center().x
                case _:
                    x = 0
            match align_y:
                case "ymin":
                    y = -bbox.bottom
                case "ymax":
                    y = -bbox.top
                case "center":
                    y = -bbox.center().y
                case _:
                    y = 0
            at = kdb.DCplxTrans(x0 + x, y0 + y)

            inst.transform(target_trans * at)
        if i_x == shape[1] - 1:
            y0 += h / 2
            x0 = 0
        else:
            x0 += w / 2
    return DInstanceGroup(
        [inst for array in insts for inst in array if inst is not None]
    )


def flexgrid(
    target: DKCell,
    kcells: Sequence[DKCell | None] | Sequence[Sequence[DKCell | None]],
    spacing: float | tuple[float, float],
    target_trans: kdb.DCplxTrans | None = None,
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] = "center",
    rotation: float = 0,
    mirror: bool = False,
) -> DInstanceGroup:
    """Create a grid of instances.

    A grid uses the bounding box of the biggest width per column and biggest height per
    row of any bounding boxes inserted into the grid.
    To this bounding box a spacing is applied in x and y.

    ```
                         spacing[0] or spacing
                        ◄─►
     ┌──────────────────┐ ┌──┬─────┬──┐ ┌──────────┐ ┌──────────┐▲
     │                  │ │  │     │  │ │          │ │          ││
     │   ┌────┐         │ │  │     │  │ │          │ │   ┌──────┼│
     │   │    │         │ │  │     │  │ │          │ │   │      ││
     │   │    │         │ │  │ big │  │ │  ┌───────┤ │   │      ││
     │   │ ▼  │         │ │  │ comp│  │ │  │       │ │   │      ││
     │   │    │         │ │  │ y   │  │ │  │       │ │   │  ▼   ││
     │   │    │         │ │  │     │  │ │  │  ▼    │ │   │      ││ y[1]
     │   └────┘         │ │  │ ▼   │  │ │  │       │ │   │      ││
     │                  │ │  │     │  │ │  │       │ │   │      ││
     │                  │ │  │     │  │ │  │       │ │   └──────┼│
     │                  │ │  │     │  │ │  │       │ │          ││
     │                  │ │  │     │  │ │  └───────┤ │          ││
     │                  │ │  │     │  │ │          │ │          ││
    ▲└──────────────────┘ └──┴─────┴──┘ └──────────┘ └──────────┘▼
    │spacing[1] or spacing
    ▼┌──────────────────┐ ┌───────────┐ ┌────┬─────┐ ┌───┬──────┐▲
     ├──────────────────┤ ├───────────┤ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │              ▼   │ │           │ │    │     │ │   │      ││
     │   big comp x     │ │           │ │    │     │ │   │      ││
     │                  │ │    ▼      │ │  ▼ │     │ │ ▼ │      ││ y[0]
     ├──────────────────┤ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     │                  │ │           │ │    │     │ │   │      ││
     └──────────────────┴─┴───────────┴─┴────┼─────┴─┴───┼──────┘►
     ►──────────────────► ►───────────► ►──────────► ►──────────►
             x[0]               x[1]        x[2]         x[3]
    ```

    Args:
        target: Target DKCell.
        kcells: Sequence or sequence of sequence of DKCells to add to the grid
        spacing: Value or tuple of value (different x/y) for spacing of the grid.
        target_trans: Apply a transformation to the whole grid before placing it.
        shape: Respace the input of kcells into an array and fill as many positions
            (first x then y).
        align_x: Align all the instance on the x-coordinate.
        align_y: Align all the instance on the y-coordinate.
        rotation: Apply a rotation to each kcells instance before adding it to the grid.
        mirror: Mirror the instances before placing them in the grid

    """
    if isinstance(spacing, tuple):
        spacing_x, spacing_y = spacing
    else:
        spacing_x = spacing
        spacing_y = spacing

    if target_trans is None:
        target_trans = kdb.DCplxTrans()

    insts: list[list[DInstance | None]]
    kcell_array: Sequence[Sequence[DKCell]]

    if shape is None:
        if isinstance(kcells[0], DKCell):
            kcell_array = cast("Sequence[list[DKCell]]", [list(kcells)])
        else:
            kcell_array = cast("Sequence[Sequence[DKCell]]", kcells)

        x0: float = 0
        y0: float = 0

        insts = [
            [
                None
                if kcell is None
                else target.create_inst(
                    kcell, kdb.DCplxTrans(1, rotation, mirror, 0, 0)
                )
                for kcell in array
            ]
            for array in kcell_array
        ]
        bboxes = [
            [None if inst is None else inst.dbbox() for inst in array]
            for array in insts
        ]
        xmin: dict[int, float] = {}
        ymin: dict[int, float] = {}
        ymax: dict[int, float] = {}
        xmax: dict[int, float] = {}
        for i_y, (array, box_array) in enumerate(zip(insts, bboxes, strict=False)):
            for i_x, (inst, bbox) in enumerate(zip(array, box_array, strict=False)):
                if inst is not None and bbox is not None:
                    match align_x:
                        case "xmin":
                            x = -bbox.left
                        case "xmax":
                            x = -bbox.right
                        case "center":
                            x = -bbox.center().x
                        case _:
                            x = 0
                    match align_y:
                        case "ymin":
                            y = -bbox.bottom
                        case "ymax":
                            y = -bbox.top
                        case "center":
                            y = -bbox.center().y
                        case _:
                            y = 0
                    at = kdb.DCplxTrans(x, y)
                    inst.dcplx_trans = at * inst.dcplx_trans
                    bbox_ = inst.dbbox()
                    xmin[i_x] = min(xmin.get(i_x) or bbox_.left, bbox_.left - spacing_x)
                    xmax[i_x] = max(xmax.get(i_x) or bbox_.right, bbox_.right)
                    ymin[i_y] = min(
                        ymin.get(i_y) or bbox_.bottom, bbox_.bottom - spacing_y
                    )
                    ymax[i_y] = max(ymax.get(i_y) or bbox_.top, bbox_.top)

        for i_y, (array, bbox_array) in enumerate(zip(insts, bboxes, strict=False)):
            y0 -= ymin.get(i_y, 0)
            for i_x, (bbox, inst) in enumerate(zip(bbox_array, array, strict=False)):
                x0 -= xmin.get(i_x, 0)
                if inst is not None and bbox is not None:
                    at = kdb.DCplxTrans(x0, y0)
                    inst.transform(target_trans * at)
                x0 += xmax.get(i_x, 0)
            y0 += ymax.get(i_y, 0)
            x0 = 0
        return DInstanceGroup(
            [inst for array in insts for inst in array if inst is not None]
        )
    _kcells: Sequence[DKCell | None]
    if isinstance(kcells[0], DKCell):
        _kcells = cast("Sequence[DKCell | None]", kcells)
    else:
        _kcells = [
            kcell
            for array in cast("Sequence[Sequence[DKCell | None]]", kcells)
            for kcell in array
        ]

    if len(_kcells) > shape[0] * shape[1]:
        raise ValueError(
            f"Shape container size {shape[0] * shape[1]=} must be bigger "
            f"than the number of kcells {len(_kcells)}"
        )

    x0 = 0
    y0 = 0

    _insts = [
        None
        if kcell is None
        else target.create_inst(kcell, kdb.DCplxTrans(1, rotation, mirror, 0, 0))
        for kcell in _kcells
    ]

    xmin = {}
    ymin = {}
    ymax = {}
    xmax = {}
    for i, inst in enumerate(_insts):
        i_x = i % shape[1]
        i_y = i // shape[1]

        if inst is not None:
            bbox = inst.dbbox()
            match align_x:
                case "xmin":
                    x = -bbox.left
                case "xmax":
                    x = -bbox.right
                case "center":
                    x = -bbox.center().x
                case _:
                    x = 0
            match align_y:
                case "ymin":
                    y = -bbox.bottom
                case "ymax":
                    y = -bbox.top
                case "center":
                    y = -bbox.center().y
                case _:
                    y = 0
            at = kdb.DCplxTrans(x, y)
            inst.dcplx_trans = at * inst.dcplx_trans
            bbox = inst.dbbox()
            xmin[i_x] = min(xmin.get(i_x) or bbox.left, bbox.left - spacing_x)
            xmax[i_x] = max(xmax.get(i_x) or bbox.right, bbox.right)
            ymin[i_y] = min(ymin.get(i_y) or bbox.bottom, bbox.bottom - spacing_y)
            ymax[i_y] = max(ymax.get(i_y) or bbox.top, bbox.top)

    insts = [[None] * shape[1] for _ in range(shape[0])]
    for i, inst in enumerate(_insts):
        i_x = i % shape[1]
        i_y = i // shape[1]
        if i_x == 0:
            y0 -= ymin.get(i_y, 0)
            x0 = 0
        else:
            x0 -= xmin.get(i_x, 0)

        if inst is not None:
            at = kdb.DCplxTrans(x0, y0)
            inst.transform(target_trans * at)
            insts[i_y][i_x] = inst
        if i_x == shape[1] - 1:
            y0 += ymax.get(i_y, 0)
            x0 = 0
        else:
            x0 += xmax.get(i_x, 0)
    return DInstanceGroup(
        [inst for array in insts for inst in array if inst is not None]
    )
