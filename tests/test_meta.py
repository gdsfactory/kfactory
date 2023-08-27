import kfactory as kf
from tempfile import NamedTemporaryFile

# def test_metainfo_set(waveguide):
#     waveguide.set_meta_data()

#     for meta in waveguide.each_meta_info():
#         if meta.name.startswith("kfactory:ports"):
#             print(meta.name, meta.value)


def test_metainfo_set(straight):
    ports = straight.ports.copy()

    straight._locked = False
    straight.set_meta_data()

    straight.ports = kf.Ports(kcl=straight.kcl)

    straight.get_meta_data()

    for i, port in enumerate(ports):
        meta_port = straight.ports[i]

        assert port.name == meta_port.name
        assert port.width == meta_port.width
        assert port.trans == meta_port.trans
        assert port.dcplx_trans == meta_port.dcplx_trans
        assert port.port_type == meta_port.port_type


def test_metainfo_read(straight):
    with NamedTemporaryFile("a") as t:
        save = kf.default_save()
        save.write_context_info = True
        straight.kcl.write(t.name)

        kcl = kf.KCLayout("TEST_META")
        kcl.read(t.name)

        wg_read = kcl[straight.name]
        wg_read.get_meta_data()
        for i, port in enumerate(straight.ports):
            read_port = wg_read.ports[i]

            assert port.name == read_port.name
            assert port.trans == read_port.trans
            assert port.dcplx_trans == read_port.dcplx_trans
            assert port.port_type == read_port.port_type
            assert port.width == read_port.width
