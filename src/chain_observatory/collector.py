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


def _latest_previous(output_root: Path) -> dict[str, Any] | None:
    paths = sorted(output_root.glob("*/*.json"))
    if not paths:
        return None
    for path in reversed(paths):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _attach_progression(result: dict[str, Any], name: str, previous: dict[str, Any] | None, now: datetime) -> None:
    result["progression"] = None
    if not previous:
        return
    previous_at = previous.get("collected_at_utc")
    previous_network = next((n for n in previous.get("networks", []) if n.get("name") == name), None)
    if not previous_at or not isinstance(previous_network, dict):
        return
    current_block = result.get("block_number")
    previous_block = previous_network.get("block_number")
    if current_block is None or previous_block is None:
        return
    try:
        prev_dt = datetime.fromisoformat(str(previous_at).replace("Z", "+00:00"))
    except ValueError:
        return
    elapsed = max(0.0, (now - prev_dt).total_seconds())
    advanced = int(current_block) - int(previous_block)
    estimated = round(elapsed / advanced, 3) if advanced > 0 else None
    result["progression"] = {
        "previous_block": int(previous_block),
        "blocks_advanced": advanced,
        "elapsed_seconds": round(elapsed, 3),
        "estimated_block_time_seconds": estimated,
    }


def collect(config_path: Path, output_root: Path, timeout: float = 12.0) -> Path | None:
    config = load_config(config_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    previous = _latest_previous(output_root)
    records: list[dict[str, Any]] = []

    for network in config["networks"]:
        if not network.get("enabled", True):
            continue
        name = str(network["name"])
        rpc_url = str(network["rpc_url"])
        expected_chain_id = network.get("expected_chain_id")
        result = probe_endpoint(rpc_url, timeout=timeout, expected_chain_id=expected_chain_id)
        result.update({
            "name": name,
            "expected_chain_id": expected_chain_id,
        })
        _attach_progression(result, name, previous, now)
        records.append(result)

    if not records or not any(item.get("ok") for item in records):
        print("No successful RPC observations; refusing to create a data commit.")
        return None

    payload = {
        "schema_version": 2,
        "collected_at_utc": now.isoformat().replace("+00:00", "Z"),
        "network_count": len(records),
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
