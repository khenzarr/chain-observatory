from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""


def fetch_snapshot(login: str, token: str) -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)
    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": start.isoformat(),
            "to": now.isoformat(),
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "chain-observatory/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if decoded.get("errors"):
        raise RuntimeError(json.dumps(decoded["errors"], sort_keys=True))
    collection = decoded["data"]["user"]["contributionsCollection"]
    return {
        "captured_at_utc": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "window_days": 365,
        "login": login,
        **collection,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot a GitHub contribution collection.")
    parser.add_argument("--login", default=os.getenv("PROFILE_LOGIN", "khenzarr"))
    parser.add_argument("--out", type=Path, default=Path("metrics/profile-latest.json"))
    args = parser.parse_args()
    token = os.getenv("PROFILE_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("No PROFILE_TOKEN/GITHUB_TOKEN available; profile snapshot skipped.")
        return 0
    try:
        snapshot = fetch_snapshot(args.login, token)
    except Exception as exc:  # noqa: BLE001 - CLI should degrade gracefully
        print(f"Profile snapshot skipped: {type(exc).__name__}: {exc}")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote profile snapshot: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
