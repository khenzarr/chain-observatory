from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .anomaly import detect_anomalies
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


def _previous_network(previous: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not previous:
        return None
    return next((n for n in previous.get("networks", []) if n.get("name") == name), None)


def _attach_progression(result: dict[str, Any], previous_network: dict[str, Any] | None,
                        previous_at: str | None, now: datetime) -> None:
    result["progression"] = None
    if not previous_network or not previous_at:
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
    previous_at = previous.get("collected_at_utc") if previous else None
    records: list[dict[str, Any]] = []

    for network in config["networks"]:
        if not network.get("enabled", True):
            continue
        name = str(network["name"])
        rpc_url = str(network["rpc_url"])
        expected_chain_id = network.get("expected_chain_id")
        prior = _previous_network(previous, name)
        result = probe_endpoint(rpc_url, timeout=timeout, expected_chain_id=expected_chain_id)
        result.update({
            "name": name,
            "family": network.get("family"),
            "expected_chain_id": expected_chain_id,
        })
        _attach_progression(result, prior, previous_at, now)
        result["anomalies"] = detect_anomalies(result, prior)
        records.append(result)

    if not records or not any(item.get("ok") for item in records):
        print("No successful RPC observations; refusing to create a data commit.")
        return None

    payload = {
        "schema_version": 3,
        "collector_version": "0.3.0",
        "sampling_interval_minutes": 15,
        "collected_at_utc": now.isoformat().replace("+00:00", "Z"),
        "network_count": len(records),
        "healthy_network_count": sum(1 for item in records if item.get("health_score", 0) >= 80),
        "anomaly_count": sum(len(item.get("anomalies", [])) for item in records),
        "networks": records,
    }

    day_dir = output_root / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    output_path = day_dir / f"{now.strftime('%H%M%S')}Z.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote observation: {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect multi-chain EVM JSON-RPC observations.")
    parser.add_argument("--config", type=Path, default=Path("config/networks.json"))
    parser.add_argument("--out", type=Path, default=Path("data/observations"))
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()
    return 0 if collect(args.config, args.out, timeout=args.timeout) else 2


if __name__ == "__main__":
    raise SystemExit(main())
