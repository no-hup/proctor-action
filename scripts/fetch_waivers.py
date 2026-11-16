#!/usr/bin/env python3
"""
Fetches and verifies GitHub-attested PR review waivers and acknowledgements from the GitHub REST API.

Outputs structured JSON matching WaiverSet:
{
  "maintainer_waivers": ["<id>", ...],
  "author_acks": ["<id>", ...]
}

Supports Policy review_mode:
- "ack" (default): Attributed acknowledgements (`proctor: ack <id>` or `proctor: accept <id>`)
  are accepted from the PR author (which clear Report-tier findings ONLY) or from any
  repository collaborator/member/owner (which clear Guard and Report tiers).
- "second_reviewer": Enforces strict non-author review from an authenticated collaborator/member/owner.
  Author acks are ignored.
- "off": Waivers and acks are disabled.
"""

import json
import os
import re
import sys
import urllib.request

WAIVER_PATTERN = re.compile(r"proctor:\s*(?:accept|ack)\s+([a-f0-9]{12})", re.IGNORECASE)
ALLOWED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

def fetch_waivers(repo: str, pr_number: str, token: str, review_mode: str) -> dict:
    empty_res = {"maintainer_waivers": [], "author_acks": []}
    if review_mode == "off":
        return empty_res

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "agent-proctor",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    # 1. Get PR details to know author login
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    req = urllib.request.Request(pr_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            pr_data = json.loads(resp.read().decode())
    except Exception as e:
        sys.stderr.write(f"proctor: warning: unable to fetch PR data: {e}\n")
        return empty_res

    pr_author = pr_data.get("user", {}).get("login", "")

    # 2. Get PR reviews and review comments
    maintainer_waivers = set()
    author_acks = set()

    endpoints = [
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews",
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments",
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    ]

    for url in endpoints:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                items = json.loads(resp.read().decode())
        except Exception:
            continue

        for item in items:
            user = item.get("user", {})
            user_login = user.get("login", "")
            user_type = user.get("type", "")
            assoc = item.get("author_association", "")

            # Never allow bots to sign off waivers
            if user_type == "Bot":
                continue

            body = item.get("body", "")
            matches = [m.group(1).lower() for m in WAIVER_PATTERN.finditer(body)]
            if not matches:
                continue

            # Non-author maintainer waivers: can waive Guard + Report
            if assoc in ALLOWED_ASSOCIATIONS and user_login != pr_author:
                maintainer_waivers.update(matches)
            # PR author acks: can ONLY waive Report (never Guard)
            elif user_login == pr_author and review_mode == "ack":
                author_acks.update(matches)

    return {
        "maintainer_waivers": sorted(list(maintainer_waivers)),
        "author_acks": sorted(list(author_acks)),
    }

def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("PR_NUMBER", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    review_mode = os.environ.get("PROCTOR_REVIEW_MODE", "ack").strip().lower()

    if not repo or not pr_number:
        print(json.dumps({"maintainer_waivers": [], "author_acks": []}))
        return

    waivers_dict = fetch_waivers(repo, pr_number, token, review_mode)
    print(json.dumps(waivers_dict))

if __name__ == "__main__":
    main()
