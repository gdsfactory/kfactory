import kfactory as kf
from collections.abc import Callable


@kf.cell
def sample(
    s: str = "a", i: int = 3, f: float = 2.0, t: tuple[int, ...] = (1,)
) -> kf.KCell:
    c = kf.KCell()
    c.info["s"] = s
    c.info["i"] = i
    c.info["f"] = f
    c.info["t"] = t
    return c


def test_settings_and_info():
    c = sample()
    assert c.info["s"] == "a"
    assert c.info["i"] == 3
    assert c.info["f"] == 2.0
    assert c.info["t"] == (1,)

    c = sample(s="b", i=4, f=3.0, t=(2, 3))
    assert c.info["s"] == "b"
    assert c.info["i"] == 4
    assert c.info["f"] == 3.0
    assert c.info["t"] == (2, 3)

    c.info["None"] = None


def test_enclosure_name(straight_factory: Callable[..., kf.KCell]) -> None:
    wg = straight_factory(width=1000, length=10000)
    assert wg.name == "Straight_W1000_L10000_LWG_EWGSTD"
    wg.show()


def test_circular_snapping(LAYER: kf.LayerEnum) -> None:
    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == b.ports["o2"].trans.disp.to_dtype(
        b.kcl.dbu
    )


def test_euler_snapping(LAYER: kf.LayerEnum) -> None:
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == b.ports["o2"].trans.disp.to_dtype(
        b.kcl.dbu
    )


def test_no_snap(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()

    c.create_port(
        dwidth=1,
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=LAYER.WG,
    )

    p = c.ports[0]

    assert p.dcplx_trans.disp != p.trans.disp.to_dtype(c.kcl.dbu)


def test_namecollision(LAYER: kf.LayerEnum) -> None:
    b1 = kf.cells.circular.bend_circular(width=1, radius=10.5, layer=LAYER.WG)
    b2 = kf.cells.circular.bend_circular(width=1, radius=10.5000005, layer=LAYER.WG)

    assert b1.name != b2.name


def test_nested_dic() -> None:
    @kf.cell(rec_dicts=True)
    def recursive_dict_cell(d: dict[str, dict[str, str] | str]) -> kf.KCell:
        c = kf.KCell()
        return c

    recursive_dict_cell({"test": {"test2": "test3"}, "test4": "test5"}).show()


def test_ports_cell(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    c.create_port(
        name="o1",
        dwidth=1,
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=LAYER.WG,
    )
    assert c["o1"]
