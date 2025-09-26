# Lab MSR

GitHub scraper: fetch the last 500 artifacts of each type: issues, pull requests, commits.

## Features
- Fetch 500 itemsper artifact type (issues, PRs, commits)
- CSV export with flattened fields
- Basic CLI options for artifact type, owner, repository, token, output directory

## Requirements
- Python 3.8+
- `python-dotenv` for loading token from `.env` (optional)

## Installation
```
pip install python-dotenv
```
(Optional if you input your token in the command. You may skip.)

## Environment Variable (Optional)
Set your token:
```
export GITHUB_TOKEN=ghp_your_token_here
```
Or create a `.env` file:
```
GITHUB_TOKEN=ghp_your_token_here
```

## Usage
Run from repository root:
```
python main.py --type issues
python main.py --type pull_requests
python main.py --type commits
```

Specify repository:
```
python main.py --owner octocat --repo Hello-World --type issues
```

Specify output directory:
```
python main.py --outdir output_data
```

Pass token explicitly:
```
python main.py --token ghp_your_token_here
```

## Output
Default directory: `data/`

Generated files (depending on --type):
- `issues.csv`
- `pull_requests.csv`
- `commits.csv`

Example columns:
- Issues: id, number, title, state, created_at, closed_at, user_login, comments, labels, labels_count
- Pull Requests: id, number, title, state, created_at, updated_at, closed_at, user_login, merged_at, draft
- Commits: sha, commit.message, commit.author.name, commit.author.date
