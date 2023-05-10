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
        for meta in waveguide.kcl.each_meta_info():
            print(f"{meta.name}: {meta.value}")

        kcl = kf.KCLayout()
        kcl.read(t.name)
        # print([cell.name for cell in kcl.cells("*")], waveguide.name)

        print()
        for meta in kcl.each_meta_info():
            print(f"{meta.name}: {meta.value}")

        wg_read = kcl[waveguide.name]
        wg_read.get_meta_data()
        print(wg_read.ports)
