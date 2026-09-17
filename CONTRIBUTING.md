# Contributing

This repository accepts changes that improve measurement quality, reproducibility, network coverage, validation, reporting, or documentation.

Generated observations are intentionally committed only when at least one real RPC call succeeds. Empty commits, timestamp-only edits, fabricated data, and synthetic contribution farming are out of scope.

For code changes:

1. Add or update tests.
2. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
3. Keep generated data separate from source code changes when practical.
