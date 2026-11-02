"""Training-only log-surface PCA and independent factor AR(1) forecasts.

No interpolation or log-order changes are hidden in this module. Inputs are
already aligned log-IV. Forecasts are one calendar observation step ahead.
"""
import numpy as np
from scipy.linalg import subspace_angles


def log_surfaces(iv, policy='strict', *, fallback=None, floor=1e-4):
    """Transform AFTER interpolation. Repairs are explicit model sensitivities.

    Strict leaves nonpositive/nonfinite cells as NaN. Linear fallback replaces
    only finite nonpositive cells; missing support is never imputed. A floor
    clips all finite values below it, so its affected count includes small IVs.
    """
    y = np.asarray(iv, float).copy()
    finite = np.isfinite(y)
    bad = finite & (y <= 0)
    changed = np.zeros(y.shape, bool)
    if policy == 'linear_fallback':
        f = np.asarray(fallback, float)
        if f.shape != y.shape or not np.all(np.isfinite(f[bad]) & (f[bad] > 0)):
            raise ValueError('Positive matching linear fallback required')
        y[bad] = f[bad]
        changed = bad
    elif policy == 'floor':
        if not np.isfinite(floor) or floor <= 0:
            raise ValueError('Floor must be positive and finite')
        changed = finite & (y < floor)
        y[changed] = floor
    elif policy != 'strict':
        raise ValueError('Unknown positivity policy')
    result = np.full(y.shape, np.nan)
    positive = np.isfinite(y) & (y > 0)
    result[positive] = np.log(y[positive])
    return result, dict(nonpositive=int(bad.sum()), repaired=int(changed.sum()),
                        nonfinite=int((~finite).sum()))


def fit_pca_ar1(train_log, month_ids, n_components=3):
    """Fit centered, unscaled PCA and OLS AR(1), using adjacent months only.

    Each call refits every historical score in the SAME training-only basis.
    There is no pooling of scores from differently rotated historical bases.
    Unstable AR slopes are reported, never silently capped.
    """
    x = np.asarray(train_log, float)
    months = np.asarray(month_ids, int)
    if (x.ndim != 2 or not np.isfinite(x).all() or len(x) < 4
            or months.shape != (len(x),) or not np.all(np.diff(months) > 0)):
        raise ValueError('Finite ordered training matrix and month IDs required')
    if not 1 <= n_components <= min(x.shape[1], len(x) - 1):
        raise ValueError('Invalid component count')
    adjacent = np.diff(months) == 1
    if adjacent.sum() < 3:
        raise ValueError('At least three adjacent training transitions required')
    mean = x.mean(axis=0)
    _, singular, vt = np.linalg.svd(x - mean, full_matrices=False)
    if singular[0] == 0 or singular[n_components-1] <= singular[0] * 1e-12:
        raise ValueError('Requested PCA subspace is rank deficient')
    loadings = vt[:n_components].T.copy()
    for j in range(n_components):
        if loadings[np.argmax(abs(loadings[:, j])), j] < 0:
            loadings[:, j] *= -1
    scores = (x - mean) @ loadings
    intercept, phi, forecast_scores = [], [], []
    for j in range(n_components):
        lag, lead = scores[:-1, j][adjacent], scores[1:, j][adjacent]
        design = np.column_stack([np.ones(len(lag)), lag])
        a, b = np.linalg.lstsq(design, lead, rcond=None)[0]
        intercept.append(a)
        phi.append(b)
        forecast_scores.append(a + b * scores[-1, j])
    eigenvalues = singular**2 / (len(x) - 1)
    return dict(mean=mean, loadings=loadings, scores=scores,
                intercept=np.array(intercept), phi=np.array(phi),
                forecast_scores=np.array(forecast_scores),
                forecast_log=mean + loadings @ np.array(forecast_scores),
                score_rw_log=mean + loadings @ scores[-1],
                explained_ratio=eigenvalues[:n_components] / eigenvalues.sum(),
                eigenvalues=eigenvalues, ar_pairs=int(adjacent.sum()))


def subspace_distance(a, b):
    """Sign/rotation-invariant maximum angle and normalized projector distance."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        raise ValueError('Subspaces must have identical dimensions')
    pc1_cosine = float(np.clip(abs(a[:,0] @ b[:,0]), 0, 1))
    # Stable near zero; arccos(sigma_min) amplifies roundoff for identical spaces.
    return dict(max_angle_degrees=float(np.degrees(np.max(subspace_angles(a, b)))),
                pc1_abs_cosine=pc1_cosine, pc1_angle_degrees=float(np.degrees(np.arccos(pc1_cosine))),
                projector_distance=float(np.linalg.norm(a @ a.T - b @ b.T, 'fro')
                                         / np.sqrt(2 * a.shape[1])))


def walk_forward(logs, month_ids, *, initial_train=24, n_components=3, window=None):
    """Yield matched chronological fits without consulting any target values.

    A training row must be valid for every interpolation method. An invalid
    origin suppresses all methods at that origin. Missing months are never
    compressed into artificial one-month AR pairs.
    """
    methods = tuple(logs)
    arrays = {m: np.asarray(logs[m], float) for m in methods}
    if not methods or len({x.shape for x in arrays.values()}) != 1:
        raise ValueError('Matching method matrices required')
    n = len(arrays[methods[0]])
    months = np.asarray(month_ids, int)
    if (months.shape != (n,) or not np.all(np.diff(months) > 0)
            or not 4 <= initial_train < n or (window is not None and window < 4)):
        raise ValueError('Invalid calendar or training window')
    for target in range(initial_train, n):
        origin = target - 1
        if months[target] - months[origin] != 1:
            yield dict(target=target, status='skipped', reason='nonadjacent target month')
            continue
        start = 0 if window is None else max(0, target - window)
        # Deliberately slice before any validity check: future values have no role.
        valid = np.logical_and.reduce([np.isfinite(x[start:target]).all(axis=1)
                                       for x in arrays.values()])
        indices = np.arange(start, target)[valid]
        if not valid[-1] or len(indices) < max(4, n_components + 1):
            yield dict(target=target, status='skipped', reason='invalid origin/insufficient training')
            continue
        fits = {m: fit_pca_ar1(x[indices], months[indices], n_components)
                for m, x in arrays.items()}
        yield dict(target=target, origin=origin, train_indices=indices,
                   status='ok', fits=fits)
