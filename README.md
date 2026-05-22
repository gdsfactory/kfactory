# KFactory 3.0.0rc2

[![codecov](https://codecov.io/gh/gdsfactory/kfactory/graph/badge.svg?token=dArcfnQE4w)](https://codecov.io/gh/gdsfactory/kfactory)

KFactory is a Python framework for photonic and electronic chip layout, built on [KLayout](https://klayout.de)'s C++ geometry engine.
It provides parametric cells with caching, optical and electrical routing, enclosures via Minkowski sums, and schematic-driven design with LVS.

## Key Features

- **Cell caching** — the `@kf.cell` decorator deduplicates identical components automatically
- **Routing** — optical and electrical bundle routing, Manhattan primitives, all-angle routing, and path-length matching
- **Cross-sections & enclosures** — define waveguide profiles and automatic boolean cladding layers via Minkowski sums
- **Schematics** — place-and-connect workflow with netlist extraction and layout-vs-schematic verification
- **Virtual cells** — hierarchical logical containers for schematic-driven design
- **Dual coordinate systems** — `KCell` (integer DBU) and `DKCell` (float µm) work side by side
- **KLayout integration** — full access to `kdb.Region`, `kdb.Polygon`, DRC, and GDS/OASIS I/O
- **Jupyter & KLive** — live preview in KLayout while editing notebooks
- **PDK system** — bundle layers, factories, cross-sections, and technology into reusable packages

## Getting Started

### Installation

KFactory is available on [PyPI](https://pypi.org/project/kfactory/) and requires Python 3.12+.

```bash
uv add kfactory

# or with pip
pip install kfactory
```

### Development

```bash
just dev
```

This installs the development environment and sets up pre-commit hooks.

## Ecosystem

| Package | Description |
|---|---|
| [gdsfactory](https://github.com/gdsfactory/gdsfactory) | Full-featured chip design framework — KFactory is its layout backend |
| [kfnetlist](https://github.com/gdsfactory/kfnetlist) | Standalone netlist extraction and generation |

## Documentation

Full documentation is available at [gdsfactory.github.io/kfactory](https://gdsfactory.github.io/kfactory).

Upgrading from an earlier version? See the [migration guide](migration.md).

## License

[MIT](LICENSE)
