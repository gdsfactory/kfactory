# Prerequisites

## Python

kfactory requires **Python 3.10+**. Familiarity with Python basics — functions, classes,
type hints, and virtual environments — will help you follow the tutorials.

A good starting point: [learnpython.org](https://www.learnpython.org/)

## Python environment

We strongly recommend using a dedicated virtual environment per project. Popular choices:

| Tool | Notes |
|------|-------|
| [uv](https://docs.astral.sh/uv/) | Fast, modern, Rust-backed. Recommended. |
| [venv](https://docs.python.org/3/library/venv.html) | Built into Python, minimal setup. |
| [conda / miniconda](https://docs.conda.io/en/latest/miniconda.html) | Good when non-Python dependencies are involved. |

## KLayout

[KLayout](https://www.klayout.de/intro.html) is the open-source GDS/OASIS viewer that kfactory
builds on. kfactory uses the `klayout` Python package internally, but having the **desktop
application** installed lets you open `.gds` files and use the `kf.show()` live preview feature.

Download: [klayout.de/build.html](https://www.klayout.de/build.html)

## klive (optional)

[klive](https://github.com/gdsfactory/klive) is a KLayout plug-in that streams GDS files
directly from Python into the running KLayout window. It is not required to run kfactory,
but it makes the interactive design loop much faster.

See [KLive Setup](klive_setup.md) for installation instructions.

## See Also

| Topic | Where |
|-------|-------|
| Installing kfactory | [Getting Started: Installation](installation.md) |
| KLive streaming setup | [Getting Started: KLive Setup](klive_setup.md) |
| 5-minute quickstart | [Getting Started: Quickstart](quickstart.py) |
