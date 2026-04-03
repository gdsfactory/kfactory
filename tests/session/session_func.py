from collections.abc import Callable

import kfactory as kf

kcl_func = kf.KCLayout("SESSION_KCL_FUNC")

cell_created = False


def make_box(size: int) -> kf.kdb.Box:
    return kf.kdb.Box(size)


@kcl_func.cell
def cell_with_func_arg(func: Callable[..., kf.kdb.Box], size: int = 500) -> kf.KCell:
    global cell_created  # noqa: PLW0603
    cell_created = True
    c = kcl_func.kcell()
    c.shapes(c.kcl.layer(1, 0)).insert(func(size))
    return c
