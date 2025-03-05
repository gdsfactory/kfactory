from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import ConfigDict

from . import kdb
from .conf import LogLevel, logger

if TYPE_CHECKING:
    from .typings import MetaData

__all__ = ["MergeDiff"]


@dataclass
class MergeDiff:
    """Dataclass to hold geometric info about the layout diff."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    layout_a: kdb.Layout
    layout_b: kdb.Layout
    name_a: str
    name_b: str
    dbu_differs: bool = False
    cell_a: kdb.Cell = field(init=False)
    cell_b: kdb.Cell = field(init=False)
    layer: kdb.LayerInfo = field(init=False)
    layer_a: int = field(init=False)
    layer_b: int = field(init=False)
    diff_xor: kdb.Layout = field(init=False)
    diff_a: kdb.Layout = field(init=False)
    diff_b: kdb.Layout = field(init=False)
    layout_meta_diff: dict[str, MetaData] = field(init=False)
    cells_meta_diff: dict[str, dict[str, MetaData]] = field(init=False)
    kdiff: kdb.LayoutDiff = field(init=False)
    loglevel: LogLevel | int = field(default=LogLevel.CRITICAL)
    """Log level at which to log polygon errors."""

    def __post_init__(self) -> None:
        """Initialize the DiffInfo."""
        self.diff_xor = kdb.Layout()
        self.layout_meta_diff = {}
        self.cells_meta_diff = defaultdict(dict)
        self.diff_a = kdb.Layout()
        self.diff_b = kdb.Layout()
        self.kdiff = kdb.LayoutDiff()
        self.kdiff.on_begin_cell = self.on_begin_cell  # type: ignore[assignment]
        self.kdiff.on_begin_layer = self.on_begin_layer  # type: ignore[assignment]
        self.kdiff.on_end_layer = self.on_end_layer  # type: ignore[assignment]
        self.kdiff.on_instance_in_a_only = self.on_instance_in_a_only  # type: ignore[assignment]
        self.kdiff.on_instance_in_b_only = self.on_instance_in_b_only  # type: ignore[assignment]
        self.kdiff.on_polygon_in_a_only = self.on_polygon_in_a_only  # type: ignore[assignment]
        self.kdiff.on_polygon_in_b_only = self.on_polygon_in_b_only  # type: ignore[assignment]
        self.kdiff.on_cell_meta_info_differs = self.on_cell_meta_info_differs  # type: ignore[assignment]

    def on_dbu_differs(self, dbu_a: float, dbu_b: float) -> None:
        """Called when the DBU differs between the two layouts."""
        if self.loglevel is not None:
            logger.log(
                self.loglevel,
                f"DBU differs between existing layout '{dbu_a!s}'"
                f" and the new layout '{dbu_b!s}'.",
            )
        self.dbu_differs = True

    def on_begin_cell(self, cell_a: kdb.Cell, cell_b: kdb.Cell) -> None:
        """Set the cells to the new cell."""
        self.cell_a = self.diff_a.create_cell(cell_a.name)
        self.cell_b = self.diff_b.create_cell(cell_b.name)

    def on_begin_layer(self, layer: kdb.LayerInfo, layer_a: int, layer_b: int) -> None:
        """Set the layers to the new layer."""
        self.layer = layer
        self.layer_a = self.diff_a.layer(layer)
        self.layer_b = self.diff_b.layer(layer)

    def on_polygon_in_a_only(self, poly: kdb.Polygon, propid: int) -> None:
        """Called when there is only a polygon in the cell_a."""
        if self.loglevel is not None:
            logger.log(self.loglevel, f"Found {poly=} in {self.name_a} only.")
        self.cell_a.shapes(self.layer_a).insert(poly)

    def on_instance_in_a_only(self, instance: kdb.CellInstArray, propid: int) -> None:
        """Called when there is only an instance in the cell_a."""
        if self.loglevel is not None:
            logger.log(self.loglevel, f"Found {instance=} in {self.name_a} only.")
        cell = self.layout_a.cell(instance.cell_index)

        regions: list[kdb.Region] = []
        layers = list(cell.layout().layer_indexes())
        layer_infos = list(cell.layout().layer_infos())

        for layer in layers:
            r = kdb.Region()
            r.insert(self.layout_a.cell(instance.cell_index).begin_shapes_rec(layer))
            regions.append(r)

        for trans in instance.each_cplx_trans():
            for li, r in zip(layer_infos, regions, strict=False):
                self.cell_a.shapes(self.diff_a.layer(li)).insert(r.transformed(trans))

    def on_instance_in_b_only(self, instance: kdb.CellInstArray, propid: int) -> None:
        """Called when there is only an instance in the cell_b."""
        if self.loglevel is not None:
            logger.log(self.loglevel, f"Found {instance=} in {self.name_b} only.")
        cell = self.layout_b.cell(instance.cell_index)

        regions: list[kdb.Region] = []
        layers = list(cell.layout().layer_indexes())
        layer_infos = list(cell.layout().layer_infos())

        for layer in layers:
            r = kdb.Region()
            r.insert(self.layout_b.cell(instance.cell_index).begin_shapes_rec(layer))
            regions.append(r)

        for trans in instance.each_cplx_trans():
            for li, r in zip(layer_infos, regions, strict=False):
                self.cell_b.shapes(self.diff_b.layer(li)).insert(r.transformed(trans))

    def on_polygon_in_b_only(self, poly: kdb.Polygon, propid: int) -> None:
        """Called when there is only a polygon in the cell_b."""
        if self.loglevel is not None:
            logger.log(self.loglevel, f"Found {poly=} in {self.name_b} only.")
        self.cell_b.shapes(self.layer_b).insert(poly)

    def on_end_layer(self) -> None:
        """Before switching to a new layer, copy the xor to the xor layout."""
        if (not self.cell_a.bbox().empty()) or (not self.cell_b.bbox().empty()):
            c: kdb.Cell = self.diff_xor.cell(self.cell_a.name)
            if c is None:
                c = self.diff_xor.create_cell(self.cell_a.name)

            c.shapes(self.diff_xor.layer(self.layer)).insert(
                kdb.Region(self.cell_a.shapes(self.layer_a))
                ^ kdb.Region(self.cell_b.shapes(self.layer_b))
            )

    def on_cell_meta_info_differs(
        self,
        name: str,
        meta_a: kdb.LayoutMetaInfo | None,
        meta_b: kdb.LayoutMetaInfo | None,
    ) -> None:
        """Called when there is a difference in meta infos of cells."""
        if meta_a is None:
            logger.log(
                self.loglevel,
                f"Found '{name}' MetaInfo in loaded Layout's cell '{self.cell_b.name}'"
                f" with value '{meta_b!s}' but it's not in the existing Layout.",
            )
        elif meta_b is None:
            logger.log(
                self.loglevel,
                f"Found '{name}' MetaInfo in existing Layout's cell '{self.cell_a.name}"
                f"' with value '{meta_a!s}' but it's not in the existing Layout.",
            )
        else:
            logger.error(
                f"'{name}' MetaInfo differs between existing '{meta_a!s}' and"
                f" loaded '{meta_b!s}'"
            )
            self.cells_meta_diff[self.cell_a.name][name] = {
                "existing": str(meta_a),
                "loaded": str(meta_b),
            }
        dc = self.diff_xor.cell(self.cell_a.name) or self.diff_xor.create_cell(
            self.cell_a.name
        )
        dc.add_meta_info(
            kdb.LayoutMetaInfo(name, {"a": meta_a, "b": meta_b}, persisted=True)
        )

    def compare(self) -> bool:
        """Run the comparing.

        Returns: True if there are differences, nothing otherwise
        """
        return self.kdiff.compare(
            self.layout_a,
            self.layout_b,
            kdb.LayoutDiff.Verbose
            | kdb.LayoutDiff.NoLayerNames
            | kdb.LayoutDiff.BoxesAsPolygons
            | kdb.LayoutDiff.PathsAsPolygons
            | kdb.LayoutDiff.IgnoreDuplicates
            | kdb.LayoutDiff.WithMetaInfo,
        )
