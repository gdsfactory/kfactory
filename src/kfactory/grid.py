"""Create 1D or 2D (flex) grids in KCells."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

import numpy as np

from . import kdb
from .conf import config
from .kcell import Instance, KCell


def grid_dbu(
    target: KCell,
    kcells: Iterable[KCell] | Iterable[list[KCell]],
    spacing: int,
    target_trans: kdb.Trans = kdb.Trans(),
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] | int = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] | int = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
    add_port_prefix: bool = True,
    add_port_suffix: bool = False,
) -> list[Instance]:
    """Adds a 1D or 2D grid into a KCell."""
    insts: list[Instance] = []

    if shape is None:
        kcell_array = np.asarray(kcells)

        if len(kcell_array.shape) == 1:
            bboxes = [c.bbox() for c in kcell_array]
            bboxes_heights = [box.height() for box in bboxes]
            bboxes_widths = [box.width() for box in bboxes]
            _bbox = kdb.Box(
                max(bboxes_widths),
                max(bboxes_heights),
            )
            w = _bbox.width() + spacing

            trans = target_trans

            for kcell, bbox in zip(kcell_array, bboxes):
                match align_x:
                    case "xmin":
                        at = kdb.Trans(-bbox.left, 0)
                    case "xmax":
                        at = kdb.Trans(-bbox.right, 0)
                    case "center":
                        at = kdb.Trans(-bbox.center().x, 0)
                    case _:
                        at = kdb.Trans(0, 0)

                insts.append(target.create_inst(kcell, trans * at))
                target.shapes(target.kcl.layer(1, 0)).insert(_bbox.transformed(trans))

                trans *= kdb.Trans(w, 0)
        else:
            bboxes = [[c.bbox() for c in array] for array in kcell_array]
            bboxes_heights = [
                [box.height() for box in box_array] for box_array in bboxes
            ]
            bboxes_widths = [[box.width() for box in box_array] for box_array in bboxes]
            _bbox = kdb.Box(
                max(max(box_array) for box_array in bboxes_widths),
                max(max(box_array) for box_array in bboxes_heights),
            )
            w = _bbox.width() + spacing
            h = _bbox.height() + spacing

            trans = target_trans

            for array, bbox_array in zip(kcell_array, bboxes):
                _trans = trans.dup()
                for kcell, bbox in zip(array, bbox_array):
                    match align_x:
                        case "xmin":
                            at = kdb.Trans(-bbox.left, 0)
                        case "xmax":
                            at = kdb.Trans(-bbox.right, 0)
                        case "center":
                            at = kdb.Trans(-bbox.center().x, 0)
                        case _:
                            at = kdb.Trans(0, 0)

                    insts.append(target.create_inst(kcell, _trans * at))
                    target.shapes(target.kcl.layer(1, 0)).insert(
                        _bbox.transformed(_trans)
                    )

                    _trans *= kdb.Trans(w, 0)

                trans *= kdb.Trans(0, h)

    elif shape is not None and len(shape) != 2:
        raise ValueError(
            "grid() shape argument must be None or"
            f" have a length of 2, for example shape=(4,6), got {shape}"
        )
    else:
        _kcells = []
        for array in kcells:
            if isinstance(array, list):
                _kcells.extend(array)

        if shape[0] * shape[1] < len(_kcells):
            raise ValueError(
                f"The shape given to the grid len={shape[0] * shape[1]} must have at "
                f"least as many slots as the amount of KCells passed, {len(_kcells)}."
            )
        bboxes = [c.bbox() for c in _kcells]
        bboxes_heights = [box.height() for box in bboxes]
        bboxes_widths = [box.width() for box in bboxes]
        _bbox = kdb.Box(
            max(bboxes_widths),
            max(bboxes_heights),
        )
        w = _bbox.width() + spacing
        h = _bbox.width() + spacing

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]

            insts.append(
                target.create_inst(kcell, trans=target_trans * kdb.Trans(x * w, y * h))
            )

    return insts


def grid_flex_dbu(
    target: KCell,
    kcells: Iterable[KCell] | Iterable[list[KCell]],
    spacing: int,
    target_trans: kdb.Trans = kdb.Trans(),
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] | int = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] | int = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
    add_port_prefix: bool = True,
    add_port_suffix: bool = False,
) -> list[Instance]:
    """Adds a 1D or 2D grid into a KCell."""
    insts: list[Instance] = []

    if shape is None:
        kcell_array = np.asarray(kcells)

        if len(kcell_array.shape) == 1:
            trans = target_trans

            for kcell in kcell_array:
                bbox = kcell.bbox()
                match align_x:
                    case "xmin":
                        at = kdb.Trans(-bbox.left, 0)
                    case "xmax":
                        at = kdb.Trans(-bbox.right, 0)
                    case "center":
                        at = kdb.Trans(-bbox.center().x, 0)
                    case _:
                        at = kdb.Trans(0, 0)

                insts.append(target.create_inst(kcell, trans * at))
                target.shapes(target.kcl.layer(1, 0)).insert(bbox.transformed(trans))

                trans *= kdb.Trans(bbox.width() + spacing, 0)
        else:
            bboxes = [[c.bbox() for c in array] for array in kcell_array]
            bboxes_heights = [
                max([box.height() for box in box_array]) for box_array in bboxes
            ]
            widths = np.asarray([[box.width() for box in array] for array in bboxes])
            bboxes_widths = np.max(widths, axis=1)
            trans = target_trans

            for y, (array, bbox_array) in enumerate(zip(kcell_array, bboxes)):
                _trans = trans.dup()
                h = bboxes_heights[y]
                for x, (kcell, bbox) in enumerate(zip(array, bbox_array)):
                    w = bboxes_widths[x]
                    _bbox = kdb.Box(w, h)
                    match align_x:
                        case "xmin":
                            at = kdb.Trans(-bbox.left, 0)
                        case "xmax":
                            at = kdb.Trans(-bbox.right, 0)
                        case "center":
                            at = kdb.Trans(-bbox.center().x, 0)
                        case _:
                            at = kdb.Trans(0, 0)

                    insts.append(target.create_inst(kcell, _trans * at))
                    target.shapes(target.kcl.layer(1, 0)).insert(
                        _bbox.transformed(_trans)
                    )

                    _trans *= kdb.Trans(w, 0)

                trans *= kdb.Trans(0, h)

    elif shape is not None and len(shape) != 2:
        raise ValueError(
            "grid() shape argument must be None or"
            f" have a length of 2, for example shape=(4,6), got {shape}"
        )
    else:
        _kcells: list[KCell] = []
        for array in kcells:
            if isinstance(array, list):
                _kcells.extend(array)

        if shape[0] * shape[1] < len(_kcells):
            raise ValueError(
                f"The shape given to the grid len={shape[0] * shape[1]} must have at "
                f"least as many slots as the amount of KCells passed, {len(_kcells)}."
            )
        _bboxes = [c.bbox() for c in _kcells]
        bboxes_heights = [box.height() for box in _bboxes]
        bboxes_widths = [box.width() for box in _bboxes]
        flex_widths: list[int] = [0] * shape[0]
        flex_heights: list[int] = [0] * shape[1]

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]
            bb = kcell.bbox()
            flex_widths[x] = max(bb.width(), flex_widths[x])
            flex_heights[y] = max(bb.height(), flex_widths[x])

        _bbox = kdb.Box(
            max(bboxes_widths),
            max(bboxes_heights),
        )
        w = _bbox.width() + spacing
        h = _bbox.width() + spacing

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]
            w = flex_widths[x] + spacing
            h = flex_heights[y] + spacing

            insts.append(
                target.create_inst(kcell, trans=target_trans * kdb.Trans(x * w, y * h))
            )

    return insts


def grid(
    target: KCell,
    kcells: Iterable[KCell] | Iterable[list[KCell]],
    spacing: float,
    target_trans: kdb.DCplxTrans = kdb.DCplxTrans(),
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] | int = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] | int = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
    add_port_prefix: bool = True,
    add_port_suffix: bool = False,
    warn_trans: bool = True,
) -> list[Instance]:
    """Adds a 1D or 2D grid into a KCell."""
    insts: list[Instance] = []

    if warn_trans and target_trans.angle not in [0.0, 90.0, 180.0, 270.0]:
        config.logger.warning(
            f"If the complex transformation is using {target_trans.angle=}"
            " different from multiples of 90°, activate "
        )

    if shape is None:
        kcell_array = np.asarray(kcells)

        if len(kcell_array.shape) == 1:
            bboxes = [c.dbbox() for c in kcell_array]
            bboxes_heights = [box.height() for box in bboxes]
            bboxes_widths = [box.width() for box in bboxes]
            _bbox = kdb.DBox(
                max(bboxes_widths),
                max(bboxes_heights),
            )
            w = _bbox.width() + spacing

            trans = target_trans

            for kcell, bbox in zip(kcell_array, bboxes):
                match align_x:
                    case "xmin":
                        at = kdb.DCplxTrans(-bbox.left, 0)
                    case "xmax":
                        at = kdb.DCplxTrans(-bbox.right, 0)
                    case "center":
                        at = kdb.DCplxTrans(-bbox.center().x, 0)
                    case _:
                        at = kdb.DCplxTrans(0, 0)

                insts.append(
                    target.create_inst(kcell, (trans * at).to_itrans(target.kcl.dbu))
                )
                target.shapes(target.kcl.layer(1, 0)).insert(_bbox.transformed(trans))

                trans *= kdb.DCplxTrans(w, 0)
        else:
            bboxes = [[c.dbbox() for c in array] for array in kcell_array]
            bboxes_heights = [
                [box.height() for box in box_array] for box_array in bboxes
            ]
            bboxes_widths = [[box.width() for box in box_array] for box_array in bboxes]
            _bbox = kdb.DBox(
                max(max(box_array) for box_array in bboxes_widths),
                max(max(box_array) for box_array in bboxes_heights),
            )
            w = _bbox.width() + spacing
            h = _bbox.height() + spacing

            trans = target_trans

            for array, bbox_array in zip(kcell_array, bboxes):
                _trans = trans.dup()
                for kcell, bbox in zip(array, bbox_array):
                    match align_x:
                        case "xmin":
                            at = kdb.DCplxTrans(-bbox.left, 0)
                        case "xmax":
                            at = kdb.DCplxTrans(-bbox.right, 0)
                        case "center":
                            at = kdb.DCplxTrans(-bbox.center().x, 0)
                        case _:
                            at = kdb.DCplxTrans(0, 0)

                    insts.append(
                        target.create_inst(
                            kcell, (trans * at).to_itrans(target.kcl.dbu)
                        )
                    )
                    target.shapes(target.kcl.layer(1, 0)).insert(
                        _bbox.transformed(_trans)
                    )

                    _trans *= kdb.DCplxTrans(w, 0)

                trans *= kdb.DCplxTrans(0, h)

    elif shape is not None and len(shape) != 2:
        raise ValueError(
            "grid() shape argument must be None or"
            f" have a length of 2, for example shape=(4,6), got {shape}"
        )
    else:
        _kcells = []
        for array in kcells:
            if isinstance(array, list):
                _kcells.extend(array)

        if shape[0] * shape[1] < len(_kcells):
            raise ValueError(
                f"The shape given to the grid len={shape[0] * shape[1]} must have at "
                f"least as many slots as the amount of KCells passed, {len(_kcells)}."
            )
        bboxes = [c.dbbox() for c in _kcells]
        bboxes_heights = [box.height() for box in bboxes]
        bboxes_widths = [box.width() for box in bboxes]
        _bbox = kdb.DBox(
            max(bboxes_widths),
            max(bboxes_heights),
        )
        w = _bbox.width() + spacing
        h = _bbox.width() + spacing

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]

            insts.append(
                target.create_inst(
                    kcell,
                    trans=(target_trans * kdb.DCplxTrans(x * w, y * h)).to_itrans(
                        target.kcl.dbu
                    ),
                ),
            )

    return insts


def grid_flex(
    target: KCell,
    kcells: Iterable[KCell] | Iterable[list[KCell]],
    spacing: float,
    target_trans: kdb.DCplxTrans = kdb.DCplxTrans(),
    shape: tuple[int, int] | None = None,
    align_x: Literal["origin", "xmin", "xmax", "center"] | int = "center",
    align_y: Literal["origin", "ymin", "ymax", "center"] | int = "center",
    rotation: Literal[0, 1, 2, 3] = 0,
    mirror: bool = False,
    add_port_prefix: bool = True,
    add_port_suffix: bool = False,
) -> list[Instance]:
    """Adds a 1D or 2D grid into a KCell."""
    insts: list[Instance] = []

    if shape is None:
        kcell_array = np.asarray(kcells)

        if len(kcell_array.shape) == 1:
            trans = target_trans

            for kcell in kcell_array:
                bbox = kcell.bbox()
                match align_x:
                    case "xmin":
                        at = kdb.DCplxTrans(-bbox.left, 0)
                    case "xmax":
                        at = kdb.DCplxTrans(-bbox.right, 0)
                    case "center":
                        at = kdb.DCplxTrans(-bbox.center().x, 0)
                    case _:
                        at = kdb.DCplxTrans(0, 0)

                insts.append(
                    target.create_inst(kcell, (trans * at).to_itrans(target.kcl.dbu))
                )
                target.shapes(target.kcl.layer(1, 0)).insert(bbox.transformed(trans))

                trans *= kdb.DCplxTrans(bbox.width() + spacing, 0)
        else:
            bboxes = [[c.bbox() for c in array] for array in kcell_array]
            bboxes_heights = [
                max([box.height() for box in box_array]) for box_array in bboxes
            ]
            widths = np.asarray([[box.width() for box in array] for array in bboxes])
            bboxes_widths = np.max(widths, axis=1)
            trans = target_trans

            for y, (array, bbox_array) in enumerate(zip(kcell_array, bboxes)):
                _trans = trans.dup()
                h = bboxes_heights[y]
                for x, (kcell, bbox) in enumerate(zip(array, bbox_array)):
                    w = bboxes_widths[x]
                    _bbox = kdb.DBox(w, h)
                    match align_x:
                        case "xmin":
                            at = kdb.DCplxTrans(-bbox.left, 0)
                        case "xmax":
                            at = kdb.DCplxTrans(-bbox.right, 0)
                        case "center":
                            at = kdb.DCplxTrans(-bbox.center().x, 0)
                        case _:
                            at = kdb.DCplxTrans(0, 0)

                    insts.append(
                        target.create_inst(
                            kcell, (_trans * at).to_itrans(target.kcl.dbu)
                        )
                    )
                    target.shapes(target.kcl.layer(1, 0)).insert(
                        _bbox.transformed(_trans)
                    )

                    _trans *= kdb.DCplxTrans(w, 0)

                trans *= kdb.DCplxTrans(0, h)

    elif shape is not None and len(shape) != 2:
        raise ValueError(
            "grid() shape argument must be None or"
            f" have a length of 2, for example shape=(4,6), got {shape}"
        )
    else:
        _kcells: list[KCell] = []
        for array in kcells:
            if isinstance(array, list):
                _kcells.extend(array)

        if shape[0] * shape[1] < len(_kcells):
            raise ValueError(
                f"The shape given to the grid len={shape[0] * shape[1]} must have at "
                f"least as many slots as the amount of KCells passed, {len(_kcells)}."
            )
        _bboxes = [c.dbbox() for c in _kcells]
        bboxes_heights = [box.height() for box in _bboxes]
        bboxes_widths = [box.width() for box in _bboxes]
        flex_widths: list[int] = [0] * shape[0]
        flex_heights: list[int] = [0] * shape[1]

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]
            bb = kcell.bbox()
            flex_widths[x] = max(bb.width(), flex_widths[x])
            flex_heights[y] = max(bb.height(), flex_widths[x])

        _bbox = kdb.DBox(
            max(bboxes_widths),
            max(bboxes_heights),
        )
        w = _bbox.width() + spacing
        h = _bbox.width() + spacing

        for i, kcell in enumerate(_kcells):
            x = i % shape[1]
            y = i // shape[1]
            w = flex_widths[x] + spacing
            h = flex_heights[y] + spacing

            insts.append(
                target.create_inst(
                    kcell,
                    trans=(target_trans * kdb.DCplxTrans(x * w, y * h)).to_itrans(
                        target.kcl.dbu
                    ),
                )
            )

    return insts
