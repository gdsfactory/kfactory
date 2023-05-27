import kfactory as kf
from tempfile import NamedTemporaryFile

# def test_metainfo_set(waveguide):
#     waveguide.set_meta_data()

#     for meta in waveguide.each_meta_info():
#         if meta.name.startswith("kfactory:ports"):
#             print(meta.name, meta.value)


def test_metainfo_set(waveguide):
    ports = waveguide.ports.copy()

    waveguide._locked = False
    waveguide.set_meta_data()

    waveguide.ports = kf.Ports(kcl=waveguide.kcl)

    waveguide.get_meta_data()

    for i, port in enumerate(ports):
        meta_port = waveguide.ports[i]

        assert port.name == meta_port.name
        assert port.width == meta_port.width
        assert port.trans == meta_port.trans
        assert port.dcplx_trans == meta_port.dcplx_trans
        assert port.port_type == meta_port.port_type


def test_metainfo_read(waveguide):
    with NamedTemporaryFile("a") as t:
        save = kf.default_save()
        save.write_context_info = True
        waveguide.kcl.write(t.name)

        kcl = kf.KCLayout()
        kcl.read(t.name)

        wg_read = kcl[waveguide.name]
        wg_read.get_meta_data()
        for i, port in enumerate(waveguide.ports):
            read_port = wg_read.ports[i]

            assert port.name == read_port.name
            assert port.trans == read_port.trans
            assert port.dcplx_trans == read_port.dcplx_trans
            assert port.port_type == read_port.port_type
            assert port.width == read_port.width
