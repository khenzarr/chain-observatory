from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") not in (1, 2, 3):
        errors.append("unsupported schema_version")
    if not isinstance(payload.get("collected_at_utc"), str):
        errors.append("missing collected_at_utc")
    networks = payload.get("networks")
    if not isinstance(networks, list) or not networks:
        errors.append("networks must be a non-empty list")
        return errors
    for index, network in enumerate(networks):
        prefix = f"networks[{index}]"
        if not isinstance(network, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not network.get("name"):
            errors.append(f"{prefix}.name missing")
        successful = network.get("successful_calls")
        total = network.get("total_calls")
        if isinstance(successful, int) and isinstance(total, int):
            if successful < 0 or total <= 0 or successful > total:
                errors.append(f"{prefix} has invalid call counts")
        score = network.get("health_score")
        if score is not None and (not isinstance(score, int) or score < 0 or score > 100):
            errors.append(f"{prefix}.health_score outside 0..100")
        anomalies = network.get("anomalies")
        if anomalies is not None and not isinstance(anomalies, list):
            errors.append(f"{prefix}.anomalies must be a list")
        capabilities = network.get("capabilities")
        if capabilities is not None and not isinstance(capabilities, dict):
            errors.append(f"{prefix}.capabilities must be an object")
    return errors


def validate_file(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["root must be an object"]
    return validate_payload(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate observatory JSON snapshots.")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path("data/observations"))
    args = parser.parse_args()
    paths = args.paths or sorted(args.root.glob("*/*.json"))[-25:]
    failed = False
    for path in paths:
        errors = validate_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}")
    if failed:
        return 1
    print(f"Validated {len(paths)} observation file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
