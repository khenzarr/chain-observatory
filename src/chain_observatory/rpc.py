from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RpcResult:
    method: str
    ok: bool
    latency_ms: float
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rpc_call(url: str, method: str, params: list[Any] | None = None, timeout: float = 12.0) -> RpcResult:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "chain-observatory/0.2"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        decoded = json.loads(body)
        if "error" in decoded:
            return RpcResult(method, False, latency_ms, error=json.dumps(decoded["error"], sort_keys=True))
        return RpcResult(method, True, latency_ms, result=decoded.get("result"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return RpcResult(method, False, latency_ms, error=f"{type(exc).__name__}: {exc}")


def parse_hex_int(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def _latest_block_metrics(block: Any, now: datetime) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    timestamp = parse_hex_int(block.get("timestamp"))
    gas_limit = parse_hex_int(block.get("gasLimit"))
    gas_used = parse_hex_int(block.get("gasUsed"))
    txs = block.get("transactions")
    result: dict[str, Any] = {
        "number": parse_hex_int(block.get("number")),
        "hash": block.get("hash"),
        "timestamp": timestamp,
        "transaction_count": len(txs) if isinstance(txs, list) else None,
        "gas_limit": gas_limit,
        "gas_used": gas_used,
        "base_fee_per_gas_wei": parse_hex_int(block.get("baseFeePerGas")),
    }
    if timestamp is not None:
        result["age_seconds"] = max(0, int(now.timestamp()) - timestamp)
    else:
        result["age_seconds"] = None
    if gas_limit and gas_used is not None:
        result["gas_utilization_pct"] = round((gas_used / gas_limit) * 100, 2)
    else:
        result["gas_utilization_pct"] = None
    return result


def _fee_history_metrics(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    base_fees = [parse_hex_int(v) for v in value.get("baseFeePerGas", [])]
    base_fees = [v for v in base_fees if v is not None]
    gas_ratios = [float(v) for v in value.get("gasUsedRatio", []) if isinstance(v, (int, float))]
    reward = value.get("reward", [])
    medians: list[int] = []
    for row in reward if isinstance(reward, list) else []:
        if isinstance(row, list) and len(row) >= 2:
            parsed = parse_hex_int(row[1])
            if parsed is not None:
                medians.append(parsed)
    return {
        "oldest_block": parse_hex_int(value.get("oldestBlock")),
        "base_fee_min_wei": min(base_fees) if base_fees else None,
        "base_fee_max_wei": max(base_fees) if base_fees else None,
        "gas_used_ratio_avg": round(sum(gas_ratios) / len(gas_ratios), 4) if gas_ratios else None,
        "priority_fee_p50_avg_wei": round(sum(medians) / len(medians)) if medians else None,
    }


def _health_score(*, success_ratio: float, latency_ms: float | None, block_age_seconds: int | None,
                  chain_id_matches_expected: bool | None) -> int:
    score = round(success_ratio * 50)
    if chain_id_matches_expected is True:
        score += 20
    elif chain_id_matches_expected is None:
        score += 10

    if latency_ms is None:
        latency_points = 0
    elif latency_ms <= 250:
        latency_points = 15
    elif latency_ms <= 750:
        latency_points = 10
    elif latency_ms <= 1500:
        latency_points = 5
    else:
        latency_points = 0
    score += latency_points

    if block_age_seconds is None:
        age_points = 5
    elif block_age_seconds <= 60:
        age_points = 15
    elif block_age_seconds <= 180:
        age_points = 10
    elif block_age_seconds <= 600:
        age_points = 5
    else:
        age_points = 0
    score += age_points
    return max(0, min(100, score))


def probe_endpoint(url: str, timeout: float = 12.0, expected_chain_id: int | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    methods = [
        ("eth_chainId", []),
        ("eth_blockNumber", []),
        ("eth_gasPrice", []),
        ("web3_clientVersion", []),
        ("eth_getBlockByNumber", ["latest", False]),
        ("eth_feeHistory", ["0x5", "latest", [10, 50, 90]]),
        ("eth_syncing", []),
        ("net_peerCount", []),
        ("net_version", []),
    ]
    calls = [_rpc_call(url, method, params, timeout=timeout) for method, params in methods]
    by_method = {item.method: item for item in calls}
    latencies = [item.latency_ms for item in calls if item.ok]

    chain_id = parse_hex_int(by_method["eth_chainId"].result)
    block_number = parse_hex_int(by_method["eth_blockNumber"].result)
    gas_price_wei = parse_hex_int(by_method["eth_gasPrice"].result)
    latest_block = _latest_block_metrics(by_method["eth_getBlockByNumber"].result, now) if by_method["eth_getBlockByNumber"].ok else None
    fee_history = _fee_history_metrics(by_method["eth_feeHistory"].result) if by_method["eth_feeHistory"].ok else None
    successful_calls = sum(1 for item in calls if item.ok)
    total_calls = len(calls)
    success_ratio = successful_calls / total_calls if total_calls else 0.0
    chain_match = (chain_id == expected_chain_id) if chain_id is not None and expected_chain_id is not None else None
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
    block_age = latest_block.get("age_seconds") if latest_block else None

    syncing_value = by_method["eth_syncing"].result if by_method["eth_syncing"].ok else None
    syncing = syncing_value is not False and syncing_value is not None

    return {
        "ok": successful_calls > 0,
        "successful_calls": successful_calls,
        "total_calls": total_calls,
        "success_ratio": round(success_ratio, 4),
        "avg_latency_ms": avg_latency,
        "chain_id": chain_id,
        "chain_id_matches_expected": chain_match,
        "block_number": block_number,
        "gas_price_wei": gas_price_wei,
        "client_version": by_method["web3_clientVersion"].result if by_method["web3_clientVersion"].ok else None,
        "net_version": by_method["net_version"].result if by_method["net_version"].ok else None,
        "peer_count": parse_hex_int(by_method["net_peerCount"].result) if by_method["net_peerCount"].ok else None,
        "syncing": syncing,
        "latest_block": latest_block,
        "fee_history": fee_history,
        "health_score": _health_score(
            success_ratio=success_ratio,
            latency_ms=avg_latency,
            block_age_seconds=block_age,
            chain_id_matches_expected=chain_match,
        ),
        "calls": [item.to_dict() for item in calls],
    }
