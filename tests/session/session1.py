import kfactory as kf

kcl1 = kf.KCLayout("SESSION_KCL1")

cell_created = False


@kcl1.cell
def test() -> kf.KCell:
    global cell_created  # noqa: PLW0603
    cell_created = True
    return kcl1.kcell()
