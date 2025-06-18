import kfactory as kf
from tests.conftest import Layers


def test_pins(layers: Layers) -> None:
    kcl_1 = kf.KCLayout("PIN_PDK", infos=Layers)

    xs = kf.SymmetricalCrossSection(
        width=5000, enclosure=kf.LayerEnclosure(main_layer=layers.METAL1, name="M1")
    )

    @kcl_1.cell
    def pad() -> kf.KCell:
        c = kcl_1.kcell()

        c.shapes(layers.METAL1).insert(kf.kdb.Box(50_000, 50_000))
        p1 = c.create_port(
            trans=kf.kdb.Trans(0, False, 25_000, 0),
            cross_section=xs,
            info={"variable_name": "p1"},
        )
        p2 = c.create_port(
            trans=kf.kdb.Trans(1, False, 0, 25_000),
            cross_section=xs,
            info={"variable_name": "p2"},
        )
        p3 = c.create_port(
            trans=kf.kdb.Trans(2, False, -25_000, 0),
            cross_section=xs,
            info={"variable_name": "p3"},
        )
        p4 = c.create_port(
            trans=kf.kdb.Trans(3, False, 0, -25_000),
            cross_section=xs,
            info={"variable_name": "p4"},
        )
        c.auto_rename_ports()

        c.create_pin(name="pin1", ports=[p1, p2, p3, p4])

        return c

    @kf.cell(basename="pad")
    def pad_tapeout() -> kf.KCell:
        c = kf.kcl.kcell()

        c.shapes(layers.METAL1).insert(kf.kdb.Box(50_000, 50_000))
        p1 = c.create_port(
            trans=kf.kdb.Trans(0, False, 25_000, 0),
            cross_section=xs,
            info={"variable_name": "p1"},
        )
        p2 = c.create_port(
            trans=kf.kdb.Trans(1, False, 0, 25_000),
            cross_section=xs,
            info={"variable_name": "p2"},
        )
        p3 = c.create_port(
            trans=kf.kdb.Trans(2, False, -25_000, 0),
            cross_section=xs,
            info={"variable_name": "p3"},
        )
        p4 = c.create_port(
            trans=kf.kdb.Trans(3, False, 0, -25_000),
            cross_section=xs,
            info={"variable_name": "p4"},
        )
        c.auto_rename_ports()

        c.create_pin(name="pin1", ports=[p1, p2, p3, p4])

        return c

    c = kf.KCell()

    pad1 = c << pad()
    pad2 = c << pad_tapeout()

    pad1.dmove((0, 200))
    pad2.dmove((200, 0))

    assert len(pad1.pins) == 1
    assert len(pad2.pins) == 1
    assert len(pad().pins) == 1
    assert len(pad_tapeout().pins) == 1

    for port in pad1.pins["pin1"].ports:
        assert port == pad1.ports[port.name]
    for port in pad2.pins["pin1"].ports:
        assert port == pad2.ports[port.name]
    for port in pad().pins["pin1"].ports:
        assert port.base is pad().ports[port.name].base
    for port in pad_tapeout().pins["pin1"].ports:
        assert port.base is pad_tapeout().ports[port.name].base

    assert len(pad().pins.filter(pin_type="DC", regex=r"^pin")) == 1
    assert len(pad().pins.filter(pin_type="RF", regex="pin1")) == 0
    assert len(pad1.pins.filter(pin_type="RF", regex="pin1")) == 0

    ci = pad1.cell.cell_index()
    ci2 = pad2.cell.cell_index()
    c.delete()
    kf.kcl[ci].delete()
    kf.kcl[ci2].delete()
