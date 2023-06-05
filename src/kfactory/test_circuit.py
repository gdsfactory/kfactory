import kfactory as kf

c = kf.KCell()

b = kf.cells.circular.bend_circular(width=1, radius=10, layer=kf.kcl.layer(1, 0))
s = kf.cells.waveguide.waveguide(width=1, length=20, layer=kf.kcl.layer(1, 0))

b1 = c << b
b2 = c << b
b2.connect("o1", b1, "o2")
b3 = c << b
b3.connect("o1", b2, "o2")
s1 = c << s
s1.connect("o1", b3, "o2")
c.add_port(b1.ports["o1"])
c.add_port(s1.ports["o2"])

nl = c.netlist()
# nl.flatten()

# for circ in nl.each_circuit_bottom_up():
#     print(circ)

print(nl)
c.show()
