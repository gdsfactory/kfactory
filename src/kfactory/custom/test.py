import kfactory as kf
import kfactory.custom as custom

kcl = kf.KCLayout("Custom")

s = custom.custom_straight(kcl)

s(width=5, length=10, c=105)
