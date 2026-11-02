# Native results for the two additional methods

These JSON files were extracted unchanged from the successful
[GitHub run 41399526405](https://github.com/jeremevans/-spine/actions/runs/41399526405).
They describe tested commit `2e0bdd0f5fe7e578bc3948c111458d80aa097bc8`.

| Directory | Artifact ID | Original archive SHA-256 |
| --- | --- | --- |
| `open-source/` | 13120833047 | `a905b9454e301dcc885e6359e66a06261543832fdc187da1d089d2d903129c0b` |
| `matlab/` | 13120138300 | `3e5a871e02e9f8a756d207daa8016af90a562c550eef8e5ebadb2eb5c1562986` |

Only the `methods/*.json` members are stored here. `open-source/` contains native
Python, Octave and R outputs plus the full comparison report; `matlab/` contains
native MATLAB and Python outputs plus its report. Both reports passed all 20
cases and 615 queries. See [the results document](../../docs/METHOD_RESULTS.md)
for versions, tolerances and coverage. Each job's NOT RUN entries refer only
to engines not executed in that job.

The fixture fingerprint identifies the shared inputs. Engine labels alone are
not cryptographic authentication; the linked CI run supplies provenance.
