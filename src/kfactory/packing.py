"""Utilities for packing KCells and Instances."""

from collections.abc import Sequence

import rpack  # type: ignore[import-untyped,unused-ignore]

from . import kdb
from .instance import Instance
from .instance_group import InstanceGroup
from .kcell import KCell

__all__ = ["pack_instances", "pack_kcells"]


def pack_kcells(
    target: KCell,
    kcells: Sequence[KCell],
    max_width: int | None = None,
    max_height: int | None = None,
    spacing: int = 0,
) -> InstanceGroup:
    """Pack KCells.

    Args:
        target: KCell to place the packed instances in.
        kcells: Sequence of KCells from which to create instances.
        max_width: Maximum width of the packed rectangle
        max_height: Maximum height of the packed rectangle
        spacing: Spacing between the instance bboxes
    """
    insts = [target << kc for kc in kcells]
    bbs = [(inst, inst.bbox()) for inst in insts]

    packed_bbs = rpack.pack(
        ((bb[1].width() + spacing, bb[1].height() + spacing) for bb in bbs),
        max_width=max_width,
        max_height=max_height,
    )

    for inst_bb, bb in zip(bbs, packed_bbs, strict=False):
        inst, _bb = inst_bb
        inst.transform(
            kdb.Trans(
                bb[0] + spacing // 2 - _bb.left, bb[1] + spacing // 2 - _bb.bottom
            )
        )

    return InstanceGroup(insts=insts)


def pack_instances(
    target: KCell,
    instances: Sequence[Instance],
    max_width: int | None = None,
    max_height: int | None = None,
    spacing: int = 0,
) -> InstanceGroup:
    """Pack KCells.

    Args:
        target: KCell to place the packed instances in.
        instances: Sequence of Instances to pack.
        max_width: Maximum width of the packed rectangle
        max_height: Maximum height of the packed rectangle
        spacing: Spacing between the instance bboxes
    """
    bbs = [(inst, inst.bbox()) for inst in instances]

    packed_bbs = rpack.pack(
        ((bb[1].width() + spacing, bb[1].height() + spacing) for bb in bbs),
        max_width=max_width,
        max_height=max_height,
    )

    for inst_bb, bb in zip(bbs, packed_bbs, strict=False):
        inst, _bb = inst_bb
        inst.transform(
            kdb.Trans(
                bb[0] + spacing // 2 - _bb.left, bb[1] + spacing // 2 - _bb.bottom
            )
        )

    return InstanceGroup(insts=instances)
