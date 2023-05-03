import kfactory as kf


def test_get_cell(pdk: kf.pdk.Pdk):
    pdk.get_cell("waveguide", width=1000, length=10000)


def test_get_enclosure(pdk: kf.pdk.Pdk):
    pdk.get_enclosure("wg")
