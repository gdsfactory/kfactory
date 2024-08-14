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


class LayerInfos(kf.LayerInfos):
    SI: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SIEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)


kf.kcl.infos = LayerInfos()
LAYER = LayerInfos()
si_enc = kf.enclosure.LayerEnclosure([(kf.kcl.infos.SIEXCLUDE, 2000)])
