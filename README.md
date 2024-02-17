# KFactory 0.11.2

Kfactory is a [gdsfactory](https://github.com/gdsfactory/gdsfactory)-like tool. It is built with [KLayout](https://klayout.de) as a backend instead of gdstk, but aims to offer the similar featuers.

| :exclamation:  KFactory is still experimental, expect API changes without notice (even though we try to keep it to a minimum!)   |
|---------------------------------------------------------------------------------------------------------------------------------|

It is suggest to pin the version of KFactory in `requirements.txt` or `pyproject.toml` with `kfactory==0.11.2` for example.

Features similar to gdsfactory:

- [x] Cells & decorator for caching & storing cells
- [x] Simple routing (point to point and simpl bundle routes for electrical routes)
- [x] Basic cells like euler/circular bends, taper, waveguide
- [x] Path extrusion (no interface with CrossSections)
- [x] Jupyter integration
- [x] PDK/package configuration
- [x] Plugin system (simulations etc.) - Check [kplugins](https://github.com/gdsfactory/kplugins)
- [x] Generic PDK example - Check [kgeneric](https://github.com/gdsfactory/kgeneric)


Notable missing Features:

- [ ] CrossSection
- [ ] Netlist/Schematics and LVS
- [ ] More advanced routing


New/Improved Features:

- Fully hierarchical bi-directional conversion to YAML
- Automatic snapping to grid thanks to KLayout
- More features for vector geometries due to concept of Point/Edge/Vector/Polygon from Klayout
- Easy booleans thanks to KLayout Regions
- Enclosures: use the concept of enclosures, similar to cross sections, to allow automatic
  calculation of boolean layers for structures based on [minkowski sum](https://en.wikipedia.org/wiki/Minkowski_addition),
  which are built into KLayout


## Installation

kfactory is available on [pypi](https://pypi.org/project/kfactory/)

```bash
pip install kfactory
```

At the moment kfactory works only on python 3.10 and above

### Development Installation


A development environment can be installed with

```bash
python -m pip install -e .[dev]
```

It is defined in `pyproject.toml`. For committing `pre-commit` should be installed with `pre-commit install`.
