import kfactory as kf

from .session1 import test

kcl2 = kf.KCLayout("SESSION_KCL2")

cell_created = False


@kcl2.cell()
def my_other_cell() -> kf.KCell:
    global cell_created  # noqa: PLW0603
    cell_created = True
    c = kcl2.kcell()
    c.shapes(c.kcl.layer(1, 0)).insert(kf.kdb.Box(500))
    c << test()
    kf.logger.info("creating other cell")
    return c
