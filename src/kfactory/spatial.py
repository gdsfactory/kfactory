"""Shared spatial-query helpers for bbox pruning and cached region extraction."""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Any

from . import kdb

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


def collect_instance_region(
    cell: Any,
    layer: int,
    inst: Any,
) -> kdb.Region:
    """Collect the actual geometry region for one instance on one layer."""
    region = kdb.Region()
    shape_it = cell.begin_shapes_rec_overlapping(layer, inst.bbox(layer))
    shape_it.select_cells([inst.cell.cell_index()])
    shape_it.min_depth = 1
    for _it in shape_it.each():
        if _it.path()[0].inst() == inst.instance:
            region.insert(_it.shape().polygon.transformed(_it.trans()))
    return region


def iter_overlapping_bbox_pairs(
    boxes: Sequence[kdb.Box],
) -> Iterator[tuple[int, int]]:
    """Yield index pairs whose bounding boxes overlap."""
    ordered = sorted(enumerate(boxes), key=lambda item: (item[1].left, item[1].bottom))
    active: dict[int, kdb.Box] = {}
    active_rights: list[tuple[int, int]] = []

    for idx, bbox in ordered:
        while active_rights and active_rights[0][0] < bbox.left:
            _, old_idx = heapq.heappop(active_rights)
            active.pop(old_idx, None)

        for other_idx, other_bbox in active.items():
            if not (other_bbox & bbox).empty():
                yield idx, other_idx

        active[idx] = bbox
        heapq.heappush(active_rights, (bbox.right, idx))
