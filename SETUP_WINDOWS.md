# Windows setup — khenzarr/chain-observatory

Chain Observatory is designed to run unattended in GitHub Actions. The local machine does not need to stay online after setup.

## Requirements

- Git
- Python 3.11+
- GitHub CLI (`gh`)

Authenticate once with `gh auth login`.

## Local validation

```powershell
cd C:\Users\mertb\Desktop\NODE\chain-observatory
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## GitHub automation

`observe.yml` runs at UTC minutes `07`, `22`, `37` and `52`. GitHub-hosted runners perform the collection, validation, report generation, commit and push. No PowerShell window, Windows scheduled task, VPS, or always-on computer is required.

The workflow uses repository variables `COMMIT_NAME` and `COMMIT_EMAIL` for transparent commit attribution.

## Guardrails

- only `khenzarr/chain-observatory` is written to
- no force-push
- no empty commits
- no timestamp-only data
- no backdating
- no issue/PR generation
- no write RPC methods or transaction signing
- no production repository access
