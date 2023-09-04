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

import kfactory as kf


class LAYER(kf.LayerEnum):
    SI = (1, 0)
    SIEXCLUDE = (1, 1)


si_enc = kf.enclosure.LayerEnclosure([(LAYER.SIEXCLUDE, 2000)])
