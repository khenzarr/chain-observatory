# Chain Observatory

A transparent, reproducible EVM network observatory that records real RPC, block, fee-market, node and health measurements on a fixed cadence and publishes raw data alongside generated reports.

This repository is intentionally separate from production application repositories. It never imports, modifies, deploys, or writes to those codebases.

## What it measures

Each observation performs read-only JSON-RPC calls including:

- `eth_chainId` / `net_version`
- `eth_blockNumber` / `eth_getBlockByNumber`
- `eth_gasPrice` / `eth_feeHistory`
- `eth_syncing` / `net_peerCount`
- `web3_clientVersion`

For every configured network, V2 stores RPC success/failure and latency plus block age, transaction count, gas utilization, base fee, fee-history summaries, client fingerprint, peer count when exposed, sync state, deterministic health score, and block progression versus the previous snapshot. Unsupported provider methods are recorded as failed calls rather than fabricated values.

## Why the raw data is committed

The repository is a time-series engineering artifact: every generated commit corresponds to a successful external measurement. There are no empty commits and no timestamp-only changes. If every RPC probe fails, the workflow exits without creating a data commit.

The automation is intentionally obvious in commit messages (`data(auto): ...`) and in this README. The goal is a useful public engineering dataset, not hidden activity.

## Cadence

The GitHub Actions workflow runs hourly at minute 23 UTC. Hourly sampling produces at most 24 scheduled data commits per day when measurements succeed. The cadence is intentionally conservative: dataset usefulness and auditability take priority over raw commit volume.

## Repository layout

```text
.
├── .github/workflows/
│   ├── observe.yml       # scheduled collector + report generation
│   └── quality.yml       # tests for source changes
├── config/
│   └── networks.json     # monitored networks
├── data/observations/    # raw immutable JSON snapshots
├── metrics/              # latest network state, daily rollups, CSV history, profile snapshot
├── reports/
│   ├── daily/            # daily aggregates
│   ├── latest.md         # latest human-readable snapshot
│   └── README.md         # report index
├── src/chain_observatory/
├── scripts/
└── tests/
```

## Local test

Python 3.11+ is sufficient; the collector uses only the standard library.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/collect.py
PYTHONPATH=src python scripts/build_report.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
python scripts/collect.py
python scripts/build_report.py
```

## One-time GitHub setup

The scheduled workflow needs one repository variable so generated commits use an email GitHub can associate with your account:

- `COMMIT_NAME` — for example `khenzarr`
- `COMMIT_EMAIL` — a verified email connected to your GitHub account, or the exact GitHub-provided noreply address shown under Settings → Emails

The repository includes `bootstrap.ps1` for creating the repository with GitHub CLI and setting both variables:

```powershell
.\bootstrap.ps1 -CommitEmail "YOUR_GITHUB_NOREPLY_OR_VERIFIED_EMAIL"
```

Do not guess the noreply address. Copy the exact address GitHub shows in your account settings.

## Optional contribution tracker

The hourly workflow also attempts to snapshot GitHub's `contributionsCollection` GraphQL data into `metrics/profile-latest.json`. Public data can often be queried with the workflow token; if you want a broader authenticated view, create a suitable token and store it as the repository secret `PROFILE_TOKEN`.

The tracker is observational only. It does not create issues, pull requests, repositories, or other activity.

## V2 data products

- immutable raw observations under `data/observations/`
- `metrics/network-latest.json` for machine-readable current state
- `metrics/daily/YYYY-MM-DD.json` daily rollups
- `metrics/daily-history.csv` analysis-friendly historical summary
- richer Markdown daily/latest reports
- schema validation before every generated commit
- deterministic health scoring and block-progression estimates

## Safety / quality rules

1. Production repositories are out of scope.
2. No empty commits.
3. No historical backdating.
4. No generated issues or PRs.
5. No fabricated measurements.
6. No commit is created when every probe fails.
7. Generated commits are labeled as automation.
8. Secrets never belong in committed config files.

## Adding another network

Add an entry to `config/networks.json`:

```json
{
  "name": "example-mainnet",
  "rpc_url": "https://example-rpc.invalid",
  "expected_chain_id": 12345,
  "enabled": true
}
```

For authenticated providers, extend the collector to read the endpoint from an Actions secret instead of committing credentials.

## License

MIT
