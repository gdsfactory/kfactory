# Installation

## Install kfactory

```bash
pip install kfactory
```

Or with [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add kfactory
```

### Optional extras

| Extra | What it adds |
|-------|-------------|
| `kfactory[git]` | Git-based layout diffing (`difftest`) |
| `kfactory[ipy]` | Jupyter / IPython display helpers (`cell.plot()`) |
| `kfactory[dev]` | Development tools (pytest, ruff, mypy, …) |

Install multiple extras at once:

```bash
pip install "kfactory[git,ipy]"
```

## Verify the installation

```python
import kfactory as kf

print(kf.__version__)

# Create a simple cell to confirm everything works
c = kf.KCell(name="hello")
c.shapes(kf.kcl.layer(1, 0)).insert(kf.kdb.Box(0, 0, 5000, 2000))
print("KCell created:", c.name)
```

If no errors appear, kfactory is installed correctly.

## Next steps

- [5-Minute Quickstart](quickstart.py) — build and connect your first components
- [KLive Setup](klive_setup.md) — stream layouts live into KLayout
- [Core Concepts: KCell](../concepts/kcell.py) — deep dive into the central class
