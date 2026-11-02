# Historical QQQ evidence provenance

- Run: https://github.com/jeremevans/-spine/actions/runs/41495485684
- Job: `quote-reconstruction` (125449206215), completed successfully.
- Code commit: `8b67526a1c19ebc53aa32886bc70b0aa831d77e6`.
- Source data commit: `anahatsingh-ui/options-dataset-hist@37f6c456fe1a4775c875673fb8ef907d5cd2fd66`.
- Artifact: `historical-qqq-evidence`, ID `13165004722`, 12,762 bytes.
- Downloaded artifact ZIP SHA-256: `ba83ba0d7200cdcd456d9082c7c6da1ffeec836dc79538847f2770de8718e9a2`.
- Market fixture fingerprint: `43df5574a12da4483068695ed5b49c79ec673aa52252566b3fb0cb280a7a449c`.

`summary.json`, `octave.log` and `r.log` were extracted unchanged from the artifact
after verifying its SHA-256 digest against GitHub's upload log. Empty logs are
expected for successful engine subprocesses. The summary includes all seven
input-file hashes, annual audits, daily fitting errors and cross-engine agreement.

Raw option quotes, generated market fixtures and per-query predictions are not
redistributed here. Rerun `scripts/historical_qqq.py --download --require Octave R`
at the named code commit to regenerate the fixtures from hash-verified inputs.
The source files must remain accessible or be supplied locally. This evidence
covers QQQ 2011-2016 sampled quote reconstruction, not NDX 2000-2016 or forecasting.
