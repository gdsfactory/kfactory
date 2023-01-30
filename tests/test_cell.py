import kfactory as kf


def test_enclosure_name(waveguide_factory):
    wg = waveguide_factory(width=1000, length=10000)
    assert wg.name == "waveguide_W1000_L10000_LWG_EWGSTD"
