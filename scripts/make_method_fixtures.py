#!/usr/bin/env python3
"""Deterministic fixtures for the two additional methods; original splines unchanged."""
import hashlib
import json
from pathlib import Path
import numpy as np
from make_fixtures import canonical

ROOT = Path(__file__).resolve().parents[1]


def make():
    rng = np.random.default_rng(483)
    cases = []
    for d in range(1, 5):
        for irregular in (False, True):
            axes = [np.linspace(0, 2 + j, 2 + j) for j in range(d)]
            if irregular:
                axes = [np.cumsum(rng.uniform(.1, 1, len(a))) for a in axes]
            nodes = np.column_stack([g.ravel(order='F') for g in np.meshgrid(*axes, indexing='ij')])
            q = rng.uniform([a[0] for a in axes], [a[-1] for a in axes], (17, d))
            outside = nodes[[0, -1]].copy(); outside[0, 0] -= .1; outside[1, -1] += .1
            q = np.vstack([nodes, q, outside])
            v = rng.uniform(.05, .8, tuple(map(len, axes)))
            cases.append(dict(name=f'linear_{d}d_{"irregular" if irregular else "uniform"}',
                method='linear', kind='grid', axes=[a.tolist() for a in axes],
                shape=list(v.shape), values=v.ravel(order='F').tolist(), queries=q.tolist(),
                fill='nan' if not irregular else -7., bandwidth=[], node_count=len(nodes)))
    # xy distinguishes bilinear tensor interpolation from triangulated linear interpolation.
    cases.append(dict(name='bilinear_xy', method='linear', kind='grid', axes=[[0., 1.], [0., 1.]],
        shape=[2, 2], values=[0., 0., 0., 1.], queries=[[.25, .5], [.75, .25]],
        fill='nan', bandwidth=[], node_count=0))
    for d in range(1, 5):
        p = rng.normal(size=(13, d)); p[-1] = p[0]  # repeated observations count twice
        cases.append(dict(name=f'nw_scattered_{d}d', method='nadaraya_watson', kind='scattered',
            points=p.tolist(), values=rng.uniform(.1, .8, len(p)).tolist(),
            queries=np.vstack([p[:2], rng.normal(size=(11, d)), np.full((1, d), 5.)]).tolist(),
            bandwidth=np.linspace(.3, 1.1, d).tolist()))
    for name, p, y, q, h in [
        ('nw_symmetric', [[-1.], [1.]], [.1, .9], [[0.], [1.]], [1.]),
        ('nw_constant', [[0., 1.], [2., 3.], [4., 2.]], [.23]*3, [[.1, .4], [8., -2.]], [.2, 2.]),
        ('nw_underflow', [[0.], [1.]], [.1, .9], [[1000.], [-1000.]], [.001]),
        ('nw_single_observation', [[1., 2.]], [.2], [[0., 0.], [9., 8.]], [1., 2.]),
    ]:
        cases.append(dict(name=name, method='nadaraya_watson', kind='scattered', points=p,
                          values=y, queries=q, bandwidth=h))
    for c in cases[2:5]:
        g = dict(c); g.update(name='nw_grid_'+c['name'], method='nadaraya_watson',
                             bandwidth=np.linspace(.4, 1.2, len(c['axes'])).tolist(), node_count=0)
        cases.append(g)
    payload = dict(description='Multilinear grid interpolation and Gaussian NW with bandwidth standard deviations', cases=cases)
    return dict(fixture_id=hashlib.sha256(canonical(payload)).hexdigest(), payload=payload)


if __name__ == '__main__':
    p = ROOT/'fixtures/methods.json'
    p.write_text(json.dumps(make(), indent=2, allow_nan=False)+'\n')
    print(p)
