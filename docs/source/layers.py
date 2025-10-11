# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: kernel_name
#     language: python
#     name: kernel_name
# ---

# This code sets up custom layer definitions and an enclosure rule for a kfactory chip layout

# SI: This is an alias for GDSII Layer 1, Datatype 0. This layer will be used for the main silicon waveguide structures.
# SIEXCLUDE: This is an alias for GDSII Layer 1, Datatype 1.
# This layer will be used to define "keep-out" zones where other silicon should not be placed.
# kf.kcl.infos = LayerInfos(): This registers the custom LayerInfos class as the globally active set of layers for the kfactory library.
# LAYER = LayerInfos(): This creates a convenient, uppercase variable LAYER that you can use in your code to access the layers
# si_enc = kf.enclosure.LayerEnclosure([(kf.kcl.infos.SIEXCLUDE, 2000)]):
# This line creates a reusable rule for drawing shapes around other shapes. An enclosure is a boundary or buffer zone on a different layer.
# Specifically, this rule (si_enc) says:
# When applied to a shape, automatically draw a new shape on the SIEXCLUDE layer that is 2000 dbu (2.0 µm) larger on all sides than the original shape.


import kfactory as kf


class LayerInfos(kf.LayerInfos):
    SI: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SIEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)


kf.kcl.infos = LayerInfos()
LAYER = LayerInfos()
si_enc = kf.enclosure.LayerEnclosure([(kf.kcl.infos.SIEXCLUDE, 2000)])
