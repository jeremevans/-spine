"""Small explicit adapter for MATLAB interpn(..., 'spline', NaN).

Contract: real finite scalar data, increasing finite axes, at least four nodes
per axis, and paired queries of shape (n_queries, n_dimensions). This adapter
deliberately rejects unsupported inputs instead of silently changing models.
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.sparse.linalg import spsolve


def validate(axes, values, queries, *, min_nodes=4):
    axes = tuple(axes)
    if any(np.iscomplexobj(a) for a in axes) or np.iscomplexobj(values) or np.iscomplexobj(queries):
        raise ValueError("Only real data are supported")
    axes = tuple(np.asarray(a, dtype=float) for a in axes)
    if not axes:
        raise ValueError("At least one axis is required")
    for a in axes:
        if a.ndim != 1 or len(a) < min_nodes or not np.isfinite(a).all() or not (np.diff(a) > 0).all():
            raise ValueError(f"Each axis must have >={min_nodes} finite strictly increasing nodes")
    values = np.asarray(values, dtype=float)
    queries = np.asarray(queries, dtype=float)
    if values.shape != tuple(map(len, axes)) or not np.isfinite(values).all():
        raise ValueError("Values must be finite and match the axis lengths exactly")
    if queries.ndim != 2 or queries.shape[1] != len(axes) or not np.isfinite(queries).all():
        raise ValueError("Queries must be a finite (n_queries, n_dimensions) matrix")
    return axes, values, queries


def interpn_spline(axes, values, queries, *, fill_value=np.nan):
    """Evaluate a tensor-product not-a-knot cubic spline.

``fill_value=None`` extends the boundary polynomial pieces. A numeric fill
replaces all out-of-domain results. Match this policy explicitly in MATLAB/R.
The direct solve reduces solver error but can be expensive in high dimensions.
Reuse RegularGridInterpolator directly if repeatedly querying the same surface.
    """
    axes, values, queries = validate(axes, values, queries)
    return RegularGridInterpolator(
        axes, values, method="cubic", solver=spsolve,
        bounds_error=False, fill_value=fill_value,
    )(queries)
