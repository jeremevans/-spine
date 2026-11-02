# Linear and Nadaraya–Watson: measured cross-language results

**PASS** in [GitHub run 41399526405](https://github.com/jeremevans/-spine/actions/runs/41399526405),
testing code commit `2e0bdd0f5fe7e578bc3948c111458d80aa097bc8`.
The run completed on 1 November 2026 Pacific time (2 November UTC).

Both GitHub jobs passed. The expanded workflow ran 22 Python unit tests, the
original 42-case/8,687-query spline suite, and this new 20-case/615-query suite.
That is **62 cases and 9,302 queries** across the three surface methods.

| New method | Cases | Query points |
| --- | ---: | ---: |
| Multilinear grid interpolation | 9 | 458 |
| Gaussian Nadaraya–Watson | 11 | 157 |

Each new method was compared to an independent 50-digit Decimal calculation.
The maximum absolute differences were:

| Engine | Linear vs reference | Gaussian NW vs reference |
| --- | ---: | ---: |
| Python | 2.220446049250313e-16 | 6.661338147750939e-16 |
| MATLAB | 1.1102230246251565e-16 | 6.661338147750939e-16 |
| Octave | 6.661338147750939e-16 | 6.661338147750939e-16 |
| R | 1.1102230246251565e-16 | 6.661338147750939e-16 |

Both CI jobs used Python 3.12.15. The native engines were MATLAB
25.2.0.3360999 (R2025b) Update 7, Octave 8.4.0, and R 4.3.3.
The MATLAB and open-source reports were generated at
`2026-11-02T06:25:09.514274+00:00` and
`2026-11-02T06:25:10.541038+00:00`, respectively.

The predeclared tolerance remains `2e-11 + 2e-10 * abs(reference)`, with matching
NaN masks and rejection of infinities. These results establish measured
agreement for the stated contracts and tested inputs, not bit-for-bit equality.
They do not assert that linear, spline and NW produce identical surfaces.

## What was exercised

- Linear interpolation on uniform and uneven grids in 1D–4D, minimum two-node
  axes, exact node recovery, numeric/NaN outside fills, and an `xy` example that
  distinguishes multilinear interpolation from triangulated interpolation.
- Gaussian NW on scattered data in 1D–4D, unequal per-coordinate bandwidths,
  duplicate observations, constant and single-observation data, extreme ordinary
  exponential underflow, and grid wrappers in 2D–3D.
- Unit tests additionally check bandwidth validation, coordinate rescaling,
  query chunking, grid ordering, constant reproduction, positivity and the
  distinction between fitting raw IV then taking logs and fitting log IV first.

MATLAB/Octave linear evaluations use native interpolation. NW is the explicit
Gaussian weighted-mean implementation supplied by this project in every language.
No separate statistics toolbox is required.

## Reproducible evidence

[Native results and provenance](../evidence/methods-41399526405/) are preserved
as unchanged JSON files extracted from the successful workflow artifacts.
The archive SHA-256 digests were verified before extraction. The root manifest
records each committed file's hash.

Fixture fingerprint:
`1b0422ec860ccc8a9bd1c31b5030905b746726ed8337e79b3457aba3e51f96dd`.

To recompute the reference and Python comparison against the saved actual
MATLAB output:

```bash
python scripts/verify_methods.py --python-only \
  --matlab-results evidence/methods-41399526405/matlab/matlab.json --require MATLAB
```

This imports saved MATLAB results. For a fresh native MATLAB run, follow the
[method guide](METHODS.md). Reports mark engines absent from an individual job
as NOT RUN: MATLAB ran in one job and Octave/R in the other.
