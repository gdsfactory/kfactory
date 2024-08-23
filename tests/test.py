import kfactory as kf

kf.kcl.infos = kf.LayerInfos(WG=kf.kdb.LayerInfo(1, 0))
kf.cells.virtual.euler.virtual_bend_euler(
    width=1, radius=30, angle=30, layer=kf.kcl.infos.WG
).show()
