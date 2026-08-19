# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import argparse
import json
import os
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a GitHub commit status pointing to the current Actions run")
    parser.add_argument("--context", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--job-status", required=True)
    args = parser.parse_args()

    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ["GITHUB_RUN_ID"]

    state = {"success": "success", "failure": "failure"}.get(args.job_status.lower(), "error")
    payload = json.dumps({
        "state": state,
        "context": args.context,
        "description": f"{args.description}: {args.job_status}"[:140],
        "target_url": f"{server_url}/{repository}/actions/runs/{run_id}",
    }).encode()
    request = urllib.request.Request(
        f"{api_url}/repos/{repository}/statuses/{sha}",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        print(f"Published {args.context}: {state} ({response.status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
