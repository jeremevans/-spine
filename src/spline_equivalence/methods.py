"""Linear grid interpolation and Gaussian Nadaraya-Watson regression."""
import operator

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .core import interpn_spline, validate


def interpn_linear(axes, values, queries, *, fill_value=np.nan):
    """Multilinear interpolation, requiring at least two nodes on each axis.

    The default outside-domain fill is NaN. ``None`` enables extrapolation.
    Interior results are convex combinations of the enclosing cell's corners.
    """
    axes, values, queries = validate(axes, values, queries, min_nodes=2)
    return RegularGridInterpolator(axes, values, method="linear",
                                   bounds_error=False, fill_value=fill_value)(queries)


def nadaraya_watson(points, values, queries, bandwidth, *, chunk_size=256):
    """Gaussian local-constant regression on scattered N-D observations.

    ``points`` is (n_samples, d), ``values`` is (n_samples,), and ``queries``
    is (n_queries, d). Bandwidths are Gaussian standard deviations in the
    coordinates' own units: a positive scalar or a length-d vector.
    Equal observation weights; duplicate observations count separately.
    The Gaussian estimator is defined outside the sample bounding box.

    Log weights are shifted before exponentiation to avoid all-zero weights.
    Extremely scaled coordinates whose squared distances overflow are rejected.
    Query chunking bounds the distance matrix size, not the number of samples.
    """
    if any(np.iscomplexobj(x) for x in (points, values, queries, bandwidth)):
        raise ValueError("Only real data and bandwidths are supported")
    p, y, q = (np.asarray(x, dtype=float) for x in (points, values, queries))
    if p.ndim != 2 or not all(p.shape) or not np.isfinite(p).all():
        raise ValueError("Points must be a nonempty finite (n_samples, d) matrix")
    if y.shape != (len(p),) or not np.isfinite(y).all():
        raise ValueError("Values must be a finite vector with one value per sample")
    if q.ndim != 2 or q.shape[1] != p.shape[1] or not np.isfinite(q).all():
        raise ValueError("Queries must be a finite (n_queries, d) matrix")
    h = np.asarray(bandwidth, dtype=float)
    if h.ndim == 0:
        h = np.full(p.shape[1], float(h))
    if h.shape != (p.shape[1],) or not np.isfinite(h).all() or not (h > 0).all():
        raise ValueError("Bandwidth must be positive and finite, scalar or length d")
    try:
        chunk_size = operator.index(chunk_size)
    except TypeError as exc:
        raise ValueError("chunk_size must be a positive integer") from exc
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    result = np.empty(len(q))
    scale = max(float(np.max(np.abs(y))), 1.0)
    for start in range(0, len(q), chunk_size):
        block = q[start:start + chunk_size]
        distances = np.zeros((len(block), len(p)))
        with np.errstate(over="ignore", invalid="ignore"):
            for j in range(p.shape[1]):
                delta = (block[:, j, None] - p[None, :, j]) / h[j]
                distances += delta * delta
        if not np.isfinite(distances).all():
            raise ValueError("Scaled distances overflow; rescale coordinates or bandwidths")
        log_weights = -0.5 * distances
        log_weights -= log_weights.max(axis=1, keepdims=True)
        weights = np.exp(log_weights)
        weights /= weights.sum(axis=1, keepdims=True)
        result[start:start + len(block)] = (weights @ (y / scale)) * scale
    return result


def interpolate_surface(axes, values, queries, *, method="spline",
                        bandwidth=None, fill_value=np.nan):
    """Select spline, multilinear, or Gaussian Nadaraya-Watson on a grid.

    All methods share the paired-query and explicit outside-fill interface.
    Nadaraya-Watson needs bandwidths and >=2 grid nodes per axis here; call
    ``nadaraya_watson`` directly for scattered data (including a single sample).
    For this grid interface ``fill_value=None`` permits outside evaluation.
    """
    if method not in ("spline", "linear", "nadaraya_watson"):
        raise ValueError("method must be spline, linear, or nadaraya_watson")
    if method != "nadaraya_watson":
        if bandwidth is not None:
            raise ValueError("bandwidth applies only to nadaraya_watson")
        fn = interpn_spline if method == "spline" else interpn_linear
        return fn(axes, values, queries, fill_value=fill_value)
    if bandwidth is None:
        raise ValueError("nadaraya_watson requires explicit bandwidths")
    axes, values, queries = validate(axes, values, queries, min_nodes=2)
    points = np.column_stack([g.ravel(order="F") for g in
                              np.meshgrid(*axes, indexing="ij")])
    outside = np.any([(queries[:, j] < a[0]) | (queries[:, j] > a[-1])
                      for j, a in enumerate(axes)], axis=0)
    # Validate bandwidths even if all queries are excluded by the fill policy.
    selected = np.ones(len(queries), dtype=bool) if fill_value is None else ~outside
    result = np.empty(len(queries))
    result[selected] = nadaraya_watson(points, values.ravel(order="F"),
                                      queries[selected], bandwidth)
    if fill_value is not None:
        result[~selected] = fill_value
    return result
