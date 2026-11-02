# Original local evidence and subsequent CI evidence

The root files below preserve the original local run. Actual MATLAB R2025b
Update 7 subsequently passed in GitHub Actions; its separate native results
and provenance are in [github-actions-41390026607/](github-actions-41390026607/).

These are actual local Python, Octave and R executions of the bundled fixtures.
The numerical suite ran on 1 November 2026. See summary.json for runtime versions,
fixture identity and per-case results. MATLAB and GitHub CI were not run as
part of that original snapshot.

The Octave output was produced by the native run_engine.m runner. After extracting
its scalar/full-grid behavior into the tested harness, the same native result
was reused while the reusable R wrapper was factored out and rerun. The final
Python comparison imported that unchanged Octave output and executed the R runner.

The example figure plots only engines present in these native result files.
unit-tests.log records the ten Python unit tests. The exact-reference answers
use fractions, not rounded values exported from any interpolation library.

Fresh runs write to results/ and do not overwrite this snapshot. See the source
manifest at the project root for file hashes. Empty native logs mean the runtime
emitted no additional stdout/stderr; the JSON files contain the numerical output.
