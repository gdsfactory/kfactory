import kfactory as kf
from kfactory.pcells.grating_coupler_elliptical import grating_coupler_elliptical


@kf.autocell
def GC_TE() -> kf.KCell:
    """
    TE grating coupler
    """
    L1 = 16600

    return grating_coupler_elliptical(
        polarization="te",
        taper_length=L1,
        taper_angle=40,
        lambda_c=1.554,
        fiber_angle=15,
        grating_line_width=343,
        wg_width=500,
        p_start=26,
        n_periods=30,
        taper_offset=-30,
        x_fiber_launch=None,
    )


@kf.autocell
def GC_TM() -> kf.KCell:
    """
    TM grating coupler
    """

    L1 = 17000

    return grating_coupler_elliptical(
        polarization="tm",
        taper_length=L1,
        taper_angle=40.0,
        lambda_c=1.58,
        fiber_angle=15.0,
        grating_line_width=550,
        wg_width=500,
        p_start=17,
        n_periods=20,
        neff=1.8,
        taper_offset=-325,
    )


if __name__ == "__main__":
    c = GC_TE()

    kf.show(c)
