import kfactory as kf


class LAYER(kf.LayerEnum):
    SI = (1, 0)
    SIEXCLUDE = (1, 1)


si_enc = kf.utils.LayerEnclosure([(LAYER.SIEXCLUDE, 2000)])
