import kfactory as kf
from tests.conftest import Layers


def test_l2n(layers: Layers) -> None:
    c = kf.KCell(name="netlist_test")

    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=layers.WG)
    s = kf.cells.straight.straight(width=1, length=20, layer=layers.WG)

    b1 = c << b
    b2 = c << b
    b2.connect("o1", b1, "o2")
    b3 = c << b
    b3.connect("o1", b2, "o2")
    s1 = c << s
    s1.connect("o1", b3, "o2")
    c.add_port(port=b1.ports["o1"])
    p = s1.ports["o2"].copy()
    p.name = None
    c.add_port(port=p)

    c.l2n()
