import klayout.db as pya


def test_shapes():
    layout = pya.Layout()
    tc = layout.create_cell("TOP")

    tc.shapes(layout.layer(1, 0)).insert(pya.Text())

    for shape in tc.shapes(layout.layer(1, 0)).each():
        print(shape.polygon)


if __name__ == "__main__":
    test_shapes()
