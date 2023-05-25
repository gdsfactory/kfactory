# Installation

In conjunction with kfactory it is highly recommended to first install KLayout, an GDS and OASIS file viewer, and and klive, the plugin for loading gds files from KFactory.

# KLayout

[KLayout](https://www.klayout.de/intro.html) is an open source viewer for files produced by kfactory. To produce these files, kfactory uses the [python package](https://pypi.org/project/klayout/)
as a basis. Therefore it is highly recommended to install KLayout. It can be downloaded from its [build](https://www.klayout.de/build.html) page

# klive

[klive](https://github.com/gdsfactory/klive) is a KLayout package that allows to load or refresh a gds from python. It can be installed with the package manager of KLayout. The following video
shows how to install it from the KLayout internal package manager. The package manager can be found in `Tools -> Manage Packages`.

![type:video](_static/klive.webm)

klive will listen on port 8082/tcp for incoming connections on localhost. When kfactory (and also gdsfactory) build a cell and want to send them to
KLayout, they will send a JSON containing the location of the GDS file and other metainfo to this port. klive will then load the gds and
execute other commands sent. This allows for instant displaying of GDS files from a CLI with python.

Sometimes the reload dialog of KLayout can interfere with klive. It can optionally be turned off in `File -> Setup -> Application -> General` under the option `Check files for updates`.

# Python Environment(s)

It is highly recommended to use a way to separate python environments and use one environment per project. There are multiple options to dos so

- [venv](https://docs.python.org/3/library/venv.html): The minimalistic way. This will create a new environment based on the base python (usually the system python for MacOS/Linux)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html): An open-source package and environment management system. Conda is not limited to python only, it also allows installation of other libraries.
  JupyterLab for example can also be installed into an environment with `conda -c conda-forge install jupyter-lab`
- [Anaconda](https://www.anaconda.com): A desktop application to manage application, packages, and environments. This contains Miniconda plus a GUI.
