import kfactory as kf

from .session2 import kcl2, my_other_cell

cell_created = False


@kcl2.cell(output_type=kf.DKCell)
def my_cell(a: int) -> kf.KCell:
    """Test function."""
    global cell_created  # noqa: PLW0603
    cell_created = True
    c = kcl2.kcell()
    c.create_inst(my_other_cell(), a=kf.kdb.Vector(1000, 0), na=a)
    kf.logger.info("creating my cell {}", a)
    return c
