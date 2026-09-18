# Chain Observatory

Chain Observatory is a transparent, reproducible multi-chain EVM observability dataset. It samples public JSON-RPC endpoints on a fixed cadence, records raw measurements, validates every snapshot, and publishes machine-readable and human-readable rollups.

The repository is deliberately isolated from application repositories: it never imports, modifies, deploys, or pushes to another codebase.

## Networks

V3 monitors six public EVM networks from one reproducible collector:

- Ethereum Mainnet
- Arc Mainnet
- Base Mainnet
- OP Mainnet
- Arbitrum One
- Avalanche C-Chain

Endpoints are declared in `config/networks.json`. No wallet, private key, transaction signing, or write RPC is used.

## What it measures

Each sample performs read-only JSON-RPC calls for chain identity, chain head, gas, latest-block metadata, node/client identity, sync state and provider capabilities. Where supported it also records fee-history, priority-fee and peer-count information.

For each network the dataset includes:

- core RPC success ratio and latency
- expected-vs-observed chain ID
- latest block number, hash and age
- transaction count and gas utilization
- gas price and EIP-1559 fee-history summaries
- client fingerprint and sync state
- block progression and estimated block time
- provider capability flags for optional methods
- deterministic 0–100 health score
- transparent rule-based anomalies

Unsupported optional methods do not artificially reduce the core endpoint health score.

## Sampling cadence

The scheduled workflow samples at minutes `07`, `22`, `37` and `52` of each UTC hour: four measurements per hour, or at most 96 scheduled observation commits per day when at least one configured endpoint returns real data.

The offsets avoid the top-of-hour scheduler hotspot. A run that cannot obtain any successful measurement exits without creating a commit. There are no empty commits and no timestamp-only commits.

## Data products

```text
.
├── config/networks.json           # monitored public endpoints
├── data/observations/YYYY-MM-DD/  # immutable raw JSON snapshots
├── metrics/
│   ├── network-latest.json        # latest normalized state
│   ├── daily/YYYY-MM-DD.json      # daily rollups
│   └── daily-history.csv          # analysis-friendly history
├── reports/
│   ├── latest.md                  # latest human-readable state
│   ├── daily/YYYY-MM-DD.md        # daily reports
│   └── README.md                  # report index
├── src/chain_observatory/
├── scripts/
└── tests/
```

Generated commits are intentionally labeled `obs(auto): ...` so automated data collection is obvious in history.

## Health and anomaly model

Health is based on four observable signals: successful core RPC calls, expected chain ID, core-call latency, and chain-head freshness. Optional provider methods are tracked as capabilities rather than treated as mandatory node-health signals.

V3 currently emits rule-based anomalies for:

- chain-ID mismatch
- low/degraded health
- stale/aging chain head
- no observed block progression over a meaningful interval
- large latency regression versus the previous sample

These rules are deterministic and stored with the raw sample; no opaque model is used.

## Reproduce locally

Python 3.11+ is sufficient and the collector uses only the standard library.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/collect.py
PYTHONPATH=src python scripts/validate_data.py
PYTHONPATH=src python scripts/build_report.py
```

PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
python scripts/collect.py
python scripts/validate_data.py
python scripts/build_report.py
```

## Automation safety properties

1. Read-only RPC methods only.
2. No wallets, private keys or transaction signing.
3. No access to any other repository.
4. No empty or backdated commits.
5. No fabricated measurements.
6. No generated issues or pull requests.
7. No commit when all configured probes fail.
8. Generated commits remain visibly automated.
9. Concurrent scheduled runs rebase normally; force-push is never used.

## Adding a network

Add a public endpoint to `config/networks.json`:

```json
{
  "name": "example-mainnet",
  "rpc_url": "https://example-rpc.invalid",
  "expected_chain_id": 12345,
  "family": "evm",
  "enabled": true
}
```

Authenticated RPC providers should be wired through Actions secrets rather than committed credentials.

## License

MIT
