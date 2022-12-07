import klayout.db as pya


def test_shapes():
    l = pya.Layout()
    tc = l.create_cell("TOP")

    tc.shapes(l.layer(1, 0)).insert(pya.Text())

    for shape in tc.shapes(l.layer(1, 0)).each():
        print(shape.polygon)


if __name__ == "__main__":
    test_shapes()
