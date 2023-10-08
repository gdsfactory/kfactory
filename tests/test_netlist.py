import kfactory as kf
import pytest


# def test_netlist(LAYER):
#     c = kf.KCell("netlist_test")

#     b = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG)
#     s = kf.cells.straight.straight(width=1, length=20, layer=LAYER.WG)

#     b1 = c << b
#     b2 = c << b
#     b2.connect("o1", b1, "o2")
#     b3 = c << b
#     b3.connect("o1", b2, "o2")
#     s1 = c << s
#     s1.connect("o1", b3, "o2")
#     c.add_port(b1.ports["o1"])
#     # c.add_port(s1.ports["o2"])
#     p = s1.ports["o2"].copy()
#     p.name = None
#     c.add_port(p)

#     nl = c.netlist()

#     print(nl.to_s())

#     nl_s = """circuit BendCircular_W1_R10_LWG_ENone_A90_AS1 (o1=o1,o2=o2);
# end;
# circuit Straight_W1000_L20000_LWG_ENone (o1=o1,o2=o2);
# end;
# circuit netlist_test (o1=o1,'1'='1');
#   subcircuit BendCircular_W1_R10_LWG_ENone_A90_AS1 '0_BendCircular_W1_R10_LWG_ENone_A90_AS1' (o1=o1,o2='0_o2-1_o1');
#   subcircuit BendCircular_W1_R10_LWG_ENone_A90_AS1 '1_BendCircular_W1_R10_LWG_ENone_A90_AS1' (o1='0_o2-1_o1',o2='1_o2-2_o1');
#   subcircuit BendCircular_W1_R10_LWG_ENone_A90_AS1 '2_BendCircular_W1_R10_LWG_ENone_A90_AS1' (o1='1_o2-2_o1',o2='2_o2-3_o1');
#   subcircuit Straight_W1000_L20000_LWG_ENone '3_Straight_W1000_L20000_LWG_ENone' (o1='2_o2-3_o1',o2='1');
# end;
# """
#     assert nl.to_s() == nl_s
#     c.show()


# def test_netlist_orientation(straight):
#     c = kf.KCell("test_nl_error")

#     s1 = c << straight
#     s2 = c << straight

#     s2.transform(kf.kdb.Trans.R90)

#     with pytest.raises(AssertionError):
#         c.netlist()


# def test_netlist_portnames(LAYER):
#     c = kf.KCell("test_netlist_portnames")

#     swg = kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
#     swgclad = kf.cells.straight.straight(width=1, length=10, layer=LAYER.WGCLAD)

#     s1 = c << swg
#     s2 = c << swg

#     sc1 = c << swgclad
#     sc2 = c << swgclad

#     s2.connect("o1", s1, "o2")
#     sc2.connect("o1", sc1, "o2")

#     c.add_port(s1.ports["o1"])
#     c.add_port(sc1.ports["o1"])

#     with pytest.raises(ValueError):
#         c.netlist()


# def test_netlist_layer(LAYER):
#     c = kf.KCell("test_netlist_layer")

#     swg = kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
#     swgclad = kf.cells.straight.straight(width=1, length=10, layer=LAYER.WGCLAD)

#     s1 = c << swg
#     s2 = c << swg

#     sc1 = c << swgclad
#     sc2 = c << swgclad

#     s2.connect("o1", s1, "o2")
#     sc2.connect("o1", sc1, "o2")

#     c.add_port(s1.ports["o1"])
#     c.add_port(sc1.ports["o1"])
#     c.add_port(s2.ports["o2"])
#     c.add_port(sc2.ports["o2"])

#     c.auto_rename_ports()

#     print(c.netlist())


def test_l2n(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell("netlist_test")

    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG)
    s = kf.cells.straight.straight(width=1, length=20, layer=LAYER.WG)

    b1 = c << b
    b2 = c << b
    b2.connect("o1", b1, "o2")
    b3 = c << b
    b3.connect("o1", b2, "o2")
    s1 = c << s
    s1.connect("o1", b3, "o2")
    c.add_port(b1.ports["o1"])
    # c.add_port(s1.ports["o2"])
    p = s1.ports["o2"].copy()
    p.name = None
    c.add_port(p)

    c.show()
    nl = c.l2n()
    print(nl)
