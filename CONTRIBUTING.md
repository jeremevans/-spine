# Extending the evidence

Keep mathematical claims, source mappings and measured execution separate.
Record missing engines as NOT RUN. Never relabel Octave results as MATLAB.

Run the unit tests and require the engines you intend to validate:

```bash
python -m unittest discover -s tests -v
python scripts/verify.py --require Octave R
```

For a new MATLAB release, use the native runner and import its output. Preserve
the fixture fingerprint and actual engine version. The verifier rejects wrong
identities, missing/duplicate cases and incompatible shapes.

Add new cases in `scripts/make_fixtures.py`, regenerate deliberately, and commit
the changed fixture with new measured outputs. Do not regenerate before
importing an existing external result. Keep the tolerance explicit; investigate
a failure before changing it. Default-solver diagnostics are distinct from
the direct-solver parity checks.

Useful next extensions include cross-engine extrapolation, 5D+ stress cases,
derivative comparisons, descending axes, small-grid fallbacks, conditioning
diagnostics and the user's original script. A claim for each extension needs
its own defined contract and evidence.
