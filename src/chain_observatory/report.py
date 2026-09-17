from __future__ import annotations

import argparse
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


def build_reports(observation_root: Path, reports_root: Path) -> None:
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
    daily_dir.mkdir(parents=True, exist_ok=True)
    for day, day_items in sorted(by_day.items()):
        lines = [
            f"# Daily RPC Report — {day}",
            "",
            f"Observations: {len(day_items)}",
            "",
            "| Network | Success | Avg latency | Block range | Chain ID |",
            "|---|---:|---:|---:|---:|",
        ]
        network_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for obs in day_items:
            for network in obs.get("networks", []):
                network_rows[str(network.get("name"))].append(network)

        for name, rows in sorted(network_rows.items()):
            success_calls = sum(int(r.get("successful_calls") or 0) for r in rows)
            total_calls = sum(int(r.get("total_calls") or 0) for r in rows)
            success_pct = round((success_calls / total_calls * 100), 1) if total_calls else 0.0
            lats = [float(r["avg_latency_ms"]) for r in rows if r.get("avg_latency_ms") is not None]
            avg_lat = round(statistics.mean(lats), 2) if lats else None
            blocks = [int(r["block_number"]) for r in rows if r.get("block_number") is not None]
            block_range = f"{min(blocks)} → {max(blocks)}" if blocks else "—"
            chain_ids = [r.get("chain_id") for r in rows if r.get("chain_id") is not None]
            chain_id = chain_ids[-1] if chain_ids else None
            lines.append(f"| {name} | {success_pct}% | {_fmt(avg_lat)} ms | {block_range} | {_fmt(chain_id)} |")

        (daily_dir / f"{day}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest = observations[-1]
    latest_time = latest.get("collected_at_utc", "unknown")
    latest_lines = [
        "# Latest RPC Observation",
        "",
        f"Collected: `{latest_time}`",
        "",
        "| Network | Status | Block | Avg latency | Gas price (wei) | Client |",
        "|---|---|---:|---:|---:|---|",
    ]
    for network in latest.get("networks", []):
        status = "OK" if network.get("ok") else "FAIL"
        latest_lines.append(
            "| {name} | {status} | {block} | {latency} | {gas} | {client} |".format(
                name=network.get("name", "unknown"),
                status=status,
                block=_fmt(network.get("block_number")),
                latency=(f"{network.get('avg_latency_ms')} ms" if network.get("avg_latency_ms") is not None else "—"),
                gas=_fmt(network.get("gas_price_wei")),
                client=str(network.get("client_version") or "—").replace("|", "\\|"),
            )
        )
    latest_lines.extend([
        "",
        "Generated automatically from the raw JSON observations committed in `data/observations/`.",
        "",
    ])
    reports_root.mkdir(parents=True, exist_ok=True)
    (reports_root / "latest.md").write_text("\n".join(latest_lines), encoding="utf-8")

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
    parser = argparse.ArgumentParser(description="Build markdown reports from observations.")
    parser.add_argument("--observations", type=Path, default=Path("data/observations"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    args = parser.parse_args()
    build_reports(args.observations, args.reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
