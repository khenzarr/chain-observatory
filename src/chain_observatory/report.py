from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_observations(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payload["_path"] = str(path)
        items.append(payload)
    return items


def _fmt(value: Any) -> str:
    return "—" if value is None else str(value)


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def build_reports(observation_root: Path, reports_root: Path, metrics_root: Path = Path("metrics")) -> None:
    observations = _read_observations(observation_root)
    if not observations:
        print("No observations available; report generation skipped.")
        return

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obs in observations:
        day = str(obs.get("collected_at_utc", ""))[:10]
        if day:
            by_day[day].append(obs)

    daily_dir = reports_root / "daily"
    daily_metrics_dir = metrics_root / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_metrics_dir.mkdir(parents=True, exist_ok=True)

    csv_rows: list[dict[str, Any]] = []
    for day, day_items in sorted(by_day.items()):
        lines = [
            f"# Daily Network Report — {day}",
            "",
            f"Observations: {len(day_items)}",
            "",
            "| Network | RPC success | Avg latency | Avg health | Block range | Avg block time | Avg gas utilization |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        network_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for obs in day_items:
            for network in obs.get("networks", []):
                network_rows[str(network.get("name"))].append(network)

        day_metric: dict[str, Any] = {"date": day, "observations": len(day_items), "networks": {}}
        for name, rows in sorted(network_rows.items()):
            success_calls = sum(int(r.get("successful_calls") or 0) for r in rows)
            total_calls = sum(int(r.get("total_calls") or 0) for r in rows)
            success_pct = round((success_calls / total_calls * 100), 2) if total_calls else 0.0
            latencies = [float(r["avg_latency_ms"]) for r in rows if r.get("avg_latency_ms") is not None]
            health = [float(r["health_score"]) for r in rows if r.get("health_score") is not None]
            blocks = [int(r["block_number"]) for r in rows if r.get("block_number") is not None]
            block_times = [float(r["progression"]["estimated_block_time_seconds"]) for r in rows if isinstance(r.get("progression"), dict) and r["progression"].get("estimated_block_time_seconds") is not None]
            utilization = [float(r["latest_block"]["gas_utilization_pct"]) for r in rows if isinstance(r.get("latest_block"), dict) and r["latest_block"].get("gas_utilization_pct") is not None]
            block_range = f"{min(blocks)} → {max(blocks)}" if blocks else "—"
            avg_latency = _mean(latencies)
            avg_health = _mean(health)
            avg_block_time = _mean(block_times)
            avg_utilization = _mean(utilization)
            lines.append(
                f"| {name} | {success_pct}% | {_fmt(avg_latency)} ms | {_fmt(avg_health)} | {block_range} | {_fmt(avg_block_time)} s | {_fmt(avg_utilization)}% |"
            )
            day_metric["networks"][name] = {
                "rpc_success_pct": success_pct,
                "avg_latency_ms": avg_latency,
                "avg_health_score": avg_health,
                "min_block": min(blocks) if blocks else None,
                "max_block": max(blocks) if blocks else None,
                "avg_estimated_block_time_seconds": avg_block_time,
                "avg_gas_utilization_pct": avg_utilization,
            }
            csv_rows.append({
                "date": day,
                "network": name,
                "observations": len(rows),
                "rpc_success_pct": success_pct,
                "avg_latency_ms": avg_latency,
                "avg_health_score": avg_health,
                "avg_estimated_block_time_seconds": avg_block_time,
                "avg_gas_utilization_pct": avg_utilization,
            })

        (daily_dir / f"{day}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (daily_metrics_dir / f"{day}.json").write_text(json.dumps(day_metric, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    latest = observations[-1]
    latest_time = latest.get("collected_at_utc", "unknown")
    latest_lines = [
        "# Latest Network Observation",
        "",
        f"Collected: `{latest_time}`",
        "",
        "| Network | Status | Health | Block | Block age | Latency | Gas | Gas use | Block time | Client |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    latest_metric: dict[str, Any] = {"captured_at_utc": latest_time, "networks": {}}
    for network in latest.get("networks", []):
        status = "OK" if network.get("ok") else "FAIL"
        latest_block = network.get("latest_block") if isinstance(network.get("latest_block"), dict) else {}
        progression = network.get("progression") if isinstance(network.get("progression"), dict) else {}
        latest_lines.append(
            "| {name} | {status} | {health} | {block} | {age} s | {latency} ms | {gas} | {util}% | {blocktime} s | {client} |".format(
                name=network.get("name", "unknown"),
                status=status,
                health=_fmt(network.get("health_score")),
                block=_fmt(network.get("block_number")),
                age=_fmt(latest_block.get("age_seconds")),
                latency=_fmt(network.get("avg_latency_ms")),
                gas=_fmt(network.get("gas_price_wei")),
                util=_fmt(latest_block.get("gas_utilization_pct")),
                blocktime=_fmt(progression.get("estimated_block_time_seconds")),
                client=str(network.get("client_version") or "—").replace("|", "\\|"),
            )
        )
        latest_metric["networks"][str(network.get("name"))] = {
            "ok": bool(network.get("ok")),
            "health_score": network.get("health_score"),
            "block_number": network.get("block_number"),
            "block_age_seconds": latest_block.get("age_seconds"),
            "avg_latency_ms": network.get("avg_latency_ms"),
            "gas_price_wei": network.get("gas_price_wei"),
            "gas_utilization_pct": latest_block.get("gas_utilization_pct"),
            "estimated_block_time_seconds": progression.get("estimated_block_time_seconds"),
        }

    latest_lines.extend(["", "Generated automatically from the immutable raw JSON snapshots in `data/observations/`.", ""])
    reports_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)
    (reports_root / "latest.md").write_text("\n".join(latest_lines), encoding="utf-8")
    (metrics_root / "network-latest.json").write_text(json.dumps(latest_metric, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (metrics_root / "daily-history.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["date", "network", "observations", "rpc_success_pct", "avg_latency_ms", "avg_health_score", "avg_estimated_block_time_seconds", "avg_gas_utilization_pct"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    index_lines = [
        "# Observatory Report Index",
        "",
        f"Updated: `{datetime.now(timezone.utc).replace(microsecond=0).isoformat()}`",
        "",
        f"Total observations: **{len(observations)}**",
        "",
        "## Daily reports",
        "",
    ]
    for day in sorted(by_day, reverse=True):
        index_lines.append(f"- [{day}](daily/{day}.md) — {len(by_day[day])} observations")
    (reports_root / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build markdown and machine-readable reports from observations.")
    parser.add_argument("--observations", type=Path, default=Path("data/observations"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--metrics", type=Path, default=Path("metrics"))
    args = parser.parse_args()
    build_reports(args.observations, args.reports, args.metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
