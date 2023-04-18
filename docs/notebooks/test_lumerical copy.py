import kfactory as kf

from kfactory.pcells.DCs import coupler
from kfactory.pcells.mzi import mzi
from kfactory.pcells import bend_euler
from kfactory.pcells.waveguide import waveguide

from kfactory.simulation.write_sparameters_lumerical import plot_sparameters_lumerical

c1 = coupler()
c1.insts[0].cell.info["sparameters"] = "C:\\Users\\schandrasekar\\Downloads\\smat_Sbend_900-1100x350_gap710_r60_h3_wlcombined2_3Dopt (1).dat"
c1.insts[2].cell.info["sparameters"] = "C:\\Users\\schandrasekar\\Downloads\\smat_Sbend_900-1100x350_gap710_r60_h3_wlcombined2_3Dopt (1).dat"
c1.insts[1].cell.info["sparameters"] = "C:\\Users\\schandrasekar\\Downloads\\MODE_3D_SiNWG_w1100x350_g840_BB (1).ldf"


bend = bend_euler(0.5, 5, 0)
bend.info["sparameters"] = "C:\\Users\\schandrasekar\\Downloads\\MODE_3D_SiNWG_r900x350_g710_BB_300K (1).ldf"


mzi1 = mzi(splitter=c1, bend_component=bend, width=0.5)

mzi1.show()

plot_sparameters_lumerical(mzi1)
