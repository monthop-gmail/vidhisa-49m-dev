#!/usr/bin/env python3
"""Restore GGS URLs from backup JSON via API."""
import json
import sys
import urllib.request


def main():
    if len(sys.argv) < 3:
        print("Usage: restore-ggs-urls.py <token> <backup.json> [api_base]")
        sys.exit(1)

    token = sys.argv[1]
    backup_file = sys.argv[2]
    api_base = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

    with open(backup_file) as f:
        branches = json.load(f)

    restored = 0
    failed = 0

    for b in branches:
        urls = {
            "ggs_url_org": b.get("ggs_url_org") or "",
            "ggs_url_participant": b.get("ggs_url_participant") or "",
            "ggs_url_record_bulk": b.get("ggs_url_record_bulk") or "",
            "ggs_url_record_ind": b.get("ggs_url_record_ind") or "",
        }
        if not any(urls.values()):
            continue

        payload = {"branch_id": b["branch_id"], **urls}
        req = urllib.request.Request(
            f"{api_base}/api/ggs/set-url",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            restored += 1
            print(f"  ✅ {b['branch_id']}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {b['branch_id']}: {e}")

    print(f"\n✅ Restored {restored} branches ({failed} failed)")


if __name__ == "__main__":
    main()
