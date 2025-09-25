Awesome—here’s a drop‑in `main.py` you can use to fetch the **last 500 Issues, Pull Requests, or Commits** for any GitHub repo, with clean CSV output.

It implements:

* CLI flag `--type {issues,pull_requests,commits}` (default: `issues`)
* `fetch_pull_requests(owner, repo)` using `/pulls?state=all&per_page=100&page=1..5`
* `fetch_commits(owner, repo)` using `/commits?per_page=100&page=1..5`
* Writes to `data/issues.csv`, `data/pull_requests.csv`, `data/commits.csv`
* Handles pagination, basic rate-limit feedback, and consistent columns

> **Auth:** (Recommended) set a personal token in `GITHUB_TOKEN` to avoid low rate limits:
>
> ```bash
> export GITHUB_TOKEN=ghp_yourtokenhere
> ```

---

## `main.py`

```python
#!/usr/bin/env python3
"""
GitHub Scraper — last 500 issues, pull requests, or commits.

Usage:
  python3 main.py --owner <org_or_user> --repo <repo_name> [--type issues|pull_requests|commits] [--outdir data] [--verbose]

Notes:
- Uses per_page=100 and pages 1..5 (up to 500 artifacts).
- For issues: filters out PRs that appear in /issues by checking 'pull_request' key.
- PRs: pulls from /pulls (state=all), includes 'merged_at' (if present) and 'draft'.
- Commits: pulls from /commits, includes 'sha', 'commit.message', 'commit.author.name', 'commit.author.date'.
- Auth: read from --token or env var GITHUB_TOKEN (recommended).
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests

GITHUB_API = "https://api.github.com"
PER_PAGE = 100
MAX_PAGES = 5  # 5 * 100 = 500


# ---------------------------
# HTTP session & pagination
# ---------------------------

def make_session(token: Optional[str] = None, verbose: bool = False) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "application/vnd.github+json",
        "User-Agent": "bug-triaging-scraper/1.0",
        # Pin to a stable API version
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = token or os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
        if verbose:
            print("→ Using GitHub token from --token or GITHUB_TOKEN")
    else:
        if verbose:
            print("⚠ No GitHub token provided. You may hit low rate limits.")
    return s


def fetch_paginated(session: requests.Session, url: str, base_params: Dict[str, Any], verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch up to 5 pages (500 items) from a list API.
    Stops early if a page returns fewer than PER_PAGE items or empty list.
    """
    all_items: List[Dict[str, Any]] = []

    for page in range(1, MAX_PAGES + 1):
        params = dict(base_params)
        params["per_page"] = PER_PAGE
        params["page"] = page

        if verbose:
            print(f"GET {url} params={params}")

        resp = session.get(url, params=params)
        # Basic rate-limit feedback
        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset = resp.headers.get("X-RateLimit-Reset")
            print("❌ Received 403 (possibly rate-limited).")
            if remaining is not None:
                print(f"   X-RateLimit-Remaining={remaining}")
            if reset is not None:
                print(f"   X-RateLimit-Reset (epoch seconds)={reset}")
            resp.raise_for_status()

        resp.raise_for_status()
        page_items = resp.json()

        # If something unexpected returns (e.g., dict with message)
        if isinstance(page_items, dict):
            msg = page_items.get("message", "Unexpected response shape.")
            raise RuntimeError(f"GitHub API error: {msg}")

        if verbose:
            print(f"   → Retrieved {len(page_items)} item(s) on page {page}")

        if not page_items:
            break

        all_items.extend(page_items)
        if len(page_items) < PER_PAGE:
            # No more full pages after this
            break

    # Return at most 500
    return all_items[: PER_PAGE * MAX_PAGES]


# ---------------------------
# Artifact fetchers
# ---------------------------

def fetch_issues(owner: str, repo: str, session: requests.Session, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    /repos/{owner}/{repo}/issues?state=all
    Note: /issues returns both issues and PRs. We filter out items with 'pull_request'.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {
        "state": "all",
        "sort": "created",
        "direction": "desc",
    }
    raw_items = fetch_paginated(session, url, params, verbose=verbose)

    # Filter out PRs masquerading as issues
    only_issues = [it for it in raw_items if "pull_request" not in it]

    def flatten(it: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": it.get("id"),
            "number": it.get("number"),
            "title": (it.get("title") or "").replace("\n", " ").strip(),
            "state": it.get("state"),
            "created_at": it.get("created_at"),
            "updated_at": it.get("updated_at"),
            "closed_at": it.get("closed_at"),
            "user.login": ((it.get("user") or {}).get("login")),
        }

    return [flatten(it) for it in only_issues][: PER_PAGE * MAX_PAGES]


def fetch_pull_requests(owner: str, repo: str, session: requests.Session, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    /repos/{owner}/{repo}/pulls?state=all
    Extract:
      id, number, title, state, created_at, updated_at, closed_at, user.login
      merged_at, draft
    Note: 'merged_at' may be null or absent on some list responses; we default to None.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {
        "state": "all",
        "sort": "created",
        "direction": "desc",
    }
    raw_items = fetch_paginated(session, url, params, verbose=verbose)

    def flatten(pr: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": pr.get("id"),
            "number": pr.get("number"),
            "title": (pr.get("title") or "").replace("\n", " ").strip(),
            "state": pr.get("state"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "closed_at": pr.get("closed_at"),
            "user.login": ((pr.get("user") or {}).get("login")),
            "merged_at": pr.get("merged_at"),  # May be absent in some list payloads
            "draft": pr.get("draft"),
        }

    return [flatten(pr) for pr in raw_items][: PER_PAGE * MAX_PAGES]


def fetch_commits(owner: str, repo: str, session: requests.Session, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    /repos/{owner}/{repo}/commits
    Extract:
      sha, commit.message, commit.author.name, commit.author.date
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {}
    raw_items = fetch_paginated(session, url, params, verbose=verbose)

    def flatten(c: Dict[str, Any]) -> Dict[str, Any]:
        commit = c.get("commit") or {}
        author = commit.get("author") or {}
        # Keep messages single-line in CSV for sanity; preserve content by escaping newlines
        msg = (commit.get("message") or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").strip()
        return {
            "sha": c.get("sha"),
            "commit.message": msg,
            "commit.author.name": author.get("name"),
            "commit.author.date": author.get("date"),
        }

    return [flatten(c) for c in raw_items][: PER_PAGE * MAX_PAGES]


# ---------------------------
# CSV writer
# ---------------------------

def write_csv(rows: List[Dict[str, Any]], fieldnames: List[str], outpath: Path, verbose: bool = False) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with outpath.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    if verbose:
        print(f"✓ Wrote {len(rows)} rows → {outpath}")


# ---------------------------
# CLI
# ---------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch last 500 issues, pull requests, or commits from a GitHub repository.")
    p.add_argument("--owner", required=True, help="Repository owner (org or user), e.g., 'microsoft'")
    p.add_argument("--repo", required=True, help="Repository name, e.g., 'vscode'")
    p.add_argument("--type", choices=["issues", "pull_requests", "commits"], default="issues",
                   help="Artifact type to fetch (default: issues)")
    p.add_argument("--outdir", default="data", help="Output directory (default: data)")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN env var)")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    session = make_session(args.token, verbose=args.verbose)
    owner, repo = args.owner, args.repo
    outdir = Path(args.outdir)

    if args.type == "issues":
        rows = fetch_issues(owner, repo, session, verbose=args.verbose)
        fields = ["id", "number", "title", "state", "created_at", "updated_at", "closed_at", "user.login"]
        outpath = outdir / "issues.csv"

    elif args.type == "pull_requests":
        rows = fetch_pull_requests(owner, repo, session, verbose=args.verbose)
        fields = ["id", "number", "title", "state", "created_at", "updated_at", "closed_at", "user.login", "merged_at", "draft"]
        outpath = outdir / "pull_requests.csv"

    else:  # commits
        rows = fetch_commits(owner, repo, session, verbose=args.verbose)
        fields = ["sha", "commit.message", "commit.author.name", "commit.author.date"]
        outpath = outdir / "commits.csv"

    # Cap at 500 just in case
    rows = rows[: PER_PAGE * MAX_PAGES]
    write_csv(rows, fields, outpath, verbose=args.verbose)

    if not rows:
        print("⚠ No data returned. Check the repo path, permissions, or whether the project has any artifacts yet.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

---

## What this writes

* **Issues:** `data/issues.csv`
  Columns: `id, number, title, state, created_at, updated_at, closed_at, user.login`
  (PRs are filtered out of the `/issues` feed.)

* **Pull Requests:** `data/pull_requests.csv`
  Columns: `id, number, title, state, created_at, updated_at, closed_at, user.login, merged_at, draft`

* **Commits:** `data/commits.csv`
  Columns: `sha, commit.message, commit.author.name, commit.author.date`
  *(Newlines in commit messages are escaped as `\n` so the CSV remains one row per commit.)*

---

## Examples

```bash
# 1) Issues (default)
python3 main.py --owner numpy --repo numpy --type issues --verbose

# 2) Pull requests
python3 main.py --owner pandas-dev --repo pandas --type pull_requests

# 3) Commits
python3 main.py --owner pydantic --repo pydantic --type commits

# Custom output directory
python3 main.py --owner octocat --repo hello-world --type issues --outdir ./data
```

---

## Notes & Tips

* **Latest 500:** The script fetches pages 1..5 with `per_page=100` (sorted newest first), which gives you the *latest* artifacts.
* **Rate limits:** Without a token, you’ll likely hit a 60 req/hour limit. With a token, you get higher limits.
* **Consistency:** Column names use dot-notation (`user.login`, `commit.message`) to match the exercise spec.
* **Extensibility:** For richer PR data (e.g., guaranteed `merged_at`), you could fetch each PR’s detail endpoint, but that adds up to 500 extra requests.

If you want me to adapt this to your existing `main.py` structure (e.g., different module layout or logging), paste your current file and I’ll merge the changes directly.

