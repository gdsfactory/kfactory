from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from .. import kdb
from ..conf import config, logger
from ..kcell import DKCell, KCell

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..typings import dbu, um


class BitMaskOperator(kdb.TileOutputReceiver):
    mask: np.typing.NDarray[np.typing._int]
    bits_per_tile: int

    def __init__(self, bpt: int) -> None:
        self.mask = np.zeros((1, 1), dtype=int)
        self.bits_per_tile = bpt

    def begin(
        self, nx: int, ny: int, p0: kdb.DPoint, dx: float, dy: float, frame: kdb.DBox
    ) -> None:
        self.mask = np.zeros(
            (ny * self.bits_per_tile, nx * self.bits_per_tile), dtype=int
        )

    def put(
        self, ix: int, iy: int, tile: kdb.Box, obj: kdb.Region, dbu: float, clip: bool
    ) -> None:
        if self.bits_per_tile > 1:
            dv = (tile.p2 - tile.p1) / self.bits_per_tile
            dx = dv.x
            dy = dv.y
            box = kdb.Box(tile.p1, tile.p1 + dv)
            for y in range(self.bits_per_tile):
                for x in range(self.bits_per_tile):
                    self.mask[iy * self.bits_per_tile + y, ix * self.bits_per_tile] = (
                        int((kdb.Region(box.moved(dx * x, dy * y)) & obj).is_empty())
                    )

        else:
            self.mask[iy, ix] = not obj.is_empty()


@overload
def bitmask(
    c: KCell,
    origin: tuple[dbu, dbu],
    rastersize: dbu,
    obstacle_layers: Sequence[tuple[kdb.LayerInfo, dbu]],
    n_threads: int | None = None,
    min_tile_size: dbu | None = None,
) -> np.typing.NDArray[np.typing._int]: ...


@overload
def bitmask(
    c: DKCell,
    origin: tuple[um, um],
    rastersize: um,
    obstacle_layers: Sequence[tuple[kdb.LayerInfo, um]],
    n_threads: int | None = None,
    min_tile_size: um | None = None,
) -> np.typing.NDArray[np.typing._int]: ...


def bitmask(
    c: KCell | DKCell,
    origin: tuple[dbu, dbu] | tuple[um, um],
    rastersize: dbu | um,
    obstacle_layers: Sequence[tuple[kdb.LayerInfo, um | dbu]],
    n_threads: int | None = None,
    min_tile_size: dbu | um | None = None,
) -> np.typing.NDArray[np.typing._int]:
    if n_threads is None:
        n_threads = config.n_threads
    if isinstance(c, KCell):
        origin = (c.kcl.to_um(origin[0]), c.kcl.to_um(origin[1]))  # type: ignore[arg-type]
        c = DKCell(base=c.base)
        rastersize = c.kcl.to_um(rastersize)  # type: ignore[arg-type]
        min_tile_size = 100 if min_tile_size is None else c.kcl.to_um(min_tile_size)  # type: ignore[arg-type]
    else:
        obstacle_layers = [
            (_layer, c.kcl.to_dbu(_size)) for _layer, _size in obstacle_layers
        ]
        min_tile_size = min_tile_size or 100

    ci = c.cell_index()

    tp = kdb.TilingProcessor()
    dbb = kdb.DBox()
    layer_names: list[str] = []
    for _layer, _size in obstacle_layers:
        dbb += c.dbbox(c.kcl.layer(_layer)).enlarged(c.kcl.to_um(_size))  # type: ignore[arg-type]
        layer_name = f"layer_{_layer.layer}_{_layer.datatype}"
        tp.input(layer_name, c.kcl.layout, ci, _layer)

        layer_names.append(layer_name)

    tp.frame = dbb  # type: ignore[misc,assignment]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads
    if rastersize < min_tile_size:
        n_raster = int(np.ceil(min_tile_size / rastersize))
        tile_size = n_raster * rastersize
        tp.tile_size(tile_size, tile_size)
        operator = BitMaskOperator(n_raster)
    else:
        tp.tile_size(rastersize, rastersize)
        operator = BitMaskOperator(1)
    border = c.kcl.to_um(max(_size for _, _size in obstacle_layers))  # type: ignore[arg-type]
    tp.tile_border(border, border)

    tp.output("bitmask", operator)

    queue_str = (
        "var mask_region = _tile & ("
        + " + ".join(
            f"{layer_name}.sized({_size})" if _size else f"{layer_name}"
            for layer_name, (_, _size) in zip(layer_names, obstacle_layers, strict=True)
        )
        + "); _output(bitmask, mask_region);"
    )

    tp.queue(queue_str)

    c.kcl.start_changes()
    try:
        name = c.kcl.future_cell_name or c.name
        logger.debug("Calculating Bitmask for {}", name)
        logger.debug("bitmask processor string: '{}'", queue_str)
        tp.execute(f"Bitmask {name}")
        logger.info("Done calculating bitmask for {}", name)
        return operator.mask  # type: ignore[no-any-return]
    finally:
        c.kcl.end_changes()
