"""Not-a-knot tensor-product interpolation on complete rectilinear grids."""
from .core import interpn_spline
from .methods import interpn_linear, nadaraya_watson, interpolate_surface

__all__ = ["interpn_spline", "interpn_linear", "nadaraya_watson", "interpolate_surface"]
