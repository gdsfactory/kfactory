from __future__ import annotations

from typing import TYPE_CHECKING

from . import kdb
from .typings import DShapeLike, IShapeLike, ShapeLike

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from .kcell import VKCell


__all__ = ["VShapes"]


class VShapes:
    """Emulate `[klayout.db.Shapes][klayout.db.Shapes]`."""

    cell: VKCell
    _shapes: list[ShapeLike]
    _bbox: kdb.DBox

    def __init__(
        self, cell: VKCell, _shapes: Sequence[ShapeLike] | None = None
    ) -> None:
        """Initialize the shapes."""
        self.cell = cell
        self._shapes = list(_shapes) if _shapes is not None else []
        self._bbox = kdb.DBox()

    def insert(self, shape: ShapeLike) -> None:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s insert'`."""
        if (
            isinstance(shape, kdb.Shape)
            and shape.cell.layout().dbu != self.cell.kcl.dbu
        ):
            raise ValueError
        if isinstance(shape, kdb.DBox):
            shape = kdb.DPolygon(shape)
        elif isinstance(shape, kdb.Box):
            shape = self.cell.kcl.to_um(shape)
        self._shapes.append(shape)
        b = shape.bbox()
        if isinstance(b, kdb.Box):
            self._bbox += self.cell.kcl.to_um(b)
        else:
            self._bbox += b

    def bbox(self) -> kdb.DBox:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s bbox'`."""
        return self._bbox.dup()

    def __iter__(self) -> Iterator[ShapeLike]:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s __iter__'`."""
        yield from self._shapes

    def each(self) -> Iterator[ShapeLike]:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s each'`."""
        yield from self._shapes

    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
    ) -> VShapes:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s transform'`."""
        new_shapes: list[DShapeLike] = []
        if isinstance(trans, kdb.Trans):
            trans = trans.to_dtype(self.cell.kcl.dbu)
        elif isinstance(trans, kdb.ICplxTrans):
            trans = trans.to_itrans(self.cell.kcl.dbu)

        for shape in self._shapes:
            if isinstance(shape, DShapeLike):
                new_shapes.append(shape.transformed(trans))
            elif isinstance(shape, IShapeLike):
                if isinstance(shape, kdb.Region):
                    new_shapes.extend(
                        poly.to_dtype(self.cell.kcl.dbu) for poly in shape.each()
                    )
                else:
                    new_shapes.append(
                        shape.to_dtype(self.cell.kcl.dbu).transformed(trans)
                    )
            else:
                new_shapes.append(shape.dpolygon.transform(trans))

        return VShapes(cell=self.cell, _shapes=new_shapes)

    def size(self) -> int:
        """Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s size'`."""
        return len(self._shapes)
