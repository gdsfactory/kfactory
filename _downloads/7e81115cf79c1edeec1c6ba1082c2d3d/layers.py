import kfactory as kf

LAYERS = {
    name: kf.library.layer(kf.kdb.LayerInfo(layer, datatype, name))  # type: ignore[call-overload]
    for name, layer, datatype in [
        ["Silicon", 1, 0],
        ["Silicon.Exclude", 1, 1],
    ]
}

si_enc = kf.utils.Enclosure([(LAYERS["Silicon.Exclude"], 2000)])
