# Actual MATLAB evidence from GitHub Actions

These four JSON files are unchanged members of the `matlab-evidence` artifact
from [run 41390026607](https://github.com/jeremevans/-spine/actions/runs/41390026607).
Both jobs in that run succeeded.

- Tested commit: `0a88379747c233227a287504adb02494d926bd45`.
- MATLAB job: `125099151863`.
- Artifact: `13116019738`, 159,172 bytes.
- Archive SHA-256: `40b31d72ec11521bb5bfe0c2b6806b30aab0ce0a62a0096d4430af9782de2db0`.
- Actual MATLAB: `25.2.0.3360999 (R2025b) Update 7`.
- Fixture: `df542b66443931554da452e934c6c93907244bac04ec2f9b3243eb4af1e1659e`.

| File | Contents |
| --- | --- |
| `matlab.json` | Actual MATLAB runner's native outputs |
| `python.json` | Python outputs from the same CI job |
| `summary.json` | Versions, tolerances and all per-case comparisons |
| `exact_reference.json` | Rational reference outputs and constraint checks |

Octave and R are marked NOT RUN in this summary because they ran in the separate
`python-octave-r` job. That job passed and produced artifact `13115904866`.
See [the CI report](../../docs/CI_RESULTS.md) for the combined run outcome.

The root manifest records individual file hashes. Native JSON engine labels
and fixture fingerprints prevent accidental mix-ups; the linked GitHub run
provides provenance. These labels alone are not cryptographic authentication
of a MATLAB installation.
