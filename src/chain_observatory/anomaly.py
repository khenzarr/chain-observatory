from __future__ import annotations

from typing import Any


def detect_anomalies(current: dict[str, Any], previous: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return transparent rule-based anomalies for one network sample."""
    anomalies: list[dict[str, Any]] = []

    if current.get("chain_id_matches_expected") is False:
        anomalies.append({"kind": "chain-id-mismatch", "severity": "critical"})

    health = current.get("health_score")
    if isinstance(health, int) and health < 60:
        anomalies.append({"kind": "low-health", "severity": "high", "value": health})
    elif isinstance(health, int) and health < 80:
        anomalies.append({"kind": "degraded-health", "severity": "medium", "value": health})

    latest_block = current.get("latest_block") if isinstance(current.get("latest_block"), dict) else {}
    age = latest_block.get("age_seconds")
    if isinstance(age, int) and age > 600:
        anomalies.append({"kind": "stale-head", "severity": "high", "value_seconds": age})
    elif isinstance(age, int) and age > 180:
        anomalies.append({"kind": "aging-head", "severity": "medium", "value_seconds": age})

    progression = current.get("progression") if isinstance(current.get("progression"), dict) else {}
    advanced = progression.get("blocks_advanced")
    elapsed = progression.get("elapsed_seconds")
    if isinstance(advanced, int) and isinstance(elapsed, (int, float)) and elapsed >= 600 and advanced <= 0:
        anomalies.append({"kind": "no-block-progression", "severity": "high", "elapsed_seconds": elapsed})

    latency = current.get("avg_latency_ms")
    previous_latency = previous.get("avg_latency_ms") if isinstance(previous, dict) else None
    if isinstance(latency, (int, float)) and isinstance(previous_latency, (int, float)):
        if previous_latency > 0 and latency >= 750 and latency >= previous_latency * 3:
            anomalies.append({
                "kind": "latency-spike",
                "severity": "medium",
                "value_ms": round(float(latency), 2),
                "previous_ms": round(float(previous_latency), 2),
            })

    return anomalies
