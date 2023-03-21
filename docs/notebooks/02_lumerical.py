# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# Simulations
# We can simulate an MZI with kfactory's Lumerical plugin
# +
from kfactory.components.mzi import mzi
from kfactory.kcell import show
from kfactory.simulation.write_sparameters_lumerical import (
    plot_sparameters_lumerical,
)
import kfactory as kf
import matplotlib.pyplot as plt
import numpy as np

mzi = mzi()
c = kf.KCell()
mzi.draw_ports()
mzi1 = c << mzi
mzi2 = c << mzi

mzi2.connect("o1", mzi1.ports["o4"])
c.add_port(port=mzi1.ports["o1"], name="o1")
c.add_port(port=mzi1.ports["o2"], name="o2")
c.add_port(port=mzi2.ports["o3"], name="o3")
c.add_port(port=mzi2.ports["o4"], name="o4")
c.draw_ports()
c.show()
plot_sparameters_lumerical(
    c,
    solver="MODE",
    dirpath="..\\test",
)
result = np.loadtxt(
    "..\\test\\ONA.csv",
    dtype=str,
    max_rows=502,
)

# -

# We can then plot the results
# +
result = result.astype(np.float64)
plt.plot(result[:, 0], result[:, 1])
mzi.flatten()
show(mzi)
# -

# mzi().write("test.gds")
