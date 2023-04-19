import kfactory as kf

from kfactory.pcells.DCs import coupler
from kfactory.pcells.mzi import mzi
from kfactory.pcells import bend_euler
from kfactory.pcells.waveguide import waveguide

from kfactory.simulation.write_sparameters_lumerical import plot_sparameters_lumerical

c1 = coupler()
c1.insts[0].cell.info["sparameters"] = "sbend sparameter.dat"
c1.insts[2].cell.info["sparameters"] = "sbend sparameters.dat"
c1.insts[1].cell.info["sparameters"] = "straight coupler.ldf"
kf.kcell.rename_clockwise(c1.ports, prefix="port")

bend = bend_euler(0.5, 5, 0)
bend.info["sparameters"] = "bend euler.ldf"

mzi1 = mzi(splitter=c1, bend_component=bend, width=0.5, port_e0_splitter="port4", port_e1_splitter="port3")

for inst in mzi1.insts:
    if "sparameters" in inst.cell.info.keys():
        continue
    inst.cell.info["sparameters"] = "straight sparameters.dat"
mzi1.show()

plot_sparameters_lumerical(mzi1)
