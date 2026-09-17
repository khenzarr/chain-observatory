from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .rpc import probe_endpoint


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("networks"), list):
        raise ValueError("config must contain a 'networks' list")
    return data


def collect(config_path: Path, output_root: Path, timeout: float = 12.0) -> Path | None:
    config = load_config(config_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    records: list[dict[str, Any]] = []

    for network in config["networks"]:
        if not network.get("enabled", True):
            continue
        name = str(network["name"])
        rpc_url = str(network["rpc_url"])
        expected_chain_id = network.get("expected_chain_id")
        result = probe_endpoint(rpc_url, timeout=timeout)
        result.update({
            "name": name,
            "expected_chain_id": expected_chain_id,
            "chain_id_matches_expected": (
                result.get("chain_id") == expected_chain_id
                if result.get("chain_id") is not None and expected_chain_id is not None
                else None
            ),
        })
        records.append(result)

    if not records or not any(item.get("ok") for item in records):
        print("No successful RPC observations; refusing to create a data commit.")
        return None

    payload = {
        "schema_version": 1,
        "collected_at_utc": now.isoformat().replace("+00:00", "Z"),
        "networks": records,
    }

    day_dir = output_root / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    output_path = day_dir / f"{now.strftime('%H%M%S')}Z.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote observation: {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect EVM JSON-RPC observations.")
    parser.add_argument("--config", type=Path, default=Path("config/networks.json"))
    parser.add_argument("--out", type=Path, default=Path("data/observations"))
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()
    return 0 if collect(args.config, args.out, timeout=args.timeout) else 2


if __name__ == "__main__":
    raise SystemExit(main())
