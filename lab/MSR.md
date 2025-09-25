# Mining the Last 500 Issues, Pull Requests, and Commits

## Goal
Extend the GitHub scraper so that it can fetch the **last 500 artifacts** of each type:

- Issues  
- Pull Requests  
- Commits  

This exercise will give you practice using the GitHub REST API, handling pagination, and preparing data for mining.

---

## Instructions (50 min)

### 1. Review the Current Scraper (5–10 min)
- Open `main.py` and see how issues are currently fetched and saved.  
- Identify where you can add new artifact types.  

### 2. Fetch Pull Requests (15 min)
- Add a new CLI flag:
  ```bash
  --type {issues,pull_requests,commits}
  ```
  (default: `issues`)  
- Implement a function:
  ```
  fetch_pull_requests(owner, repo)
  ```
  using:
  ```
  GET https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=100&page=1..5
  ```
- Extract at least these fields:
  - `id`, `number`, `title`, `state`, `created_at`, `updated_at`, `closed_at`, `user.login`
  - PR-specific: `merged_at`, `draft`

### 3. Fetch Commits (15 min)
- Implement a function:
  ```
  fetch_commits(owner, repo)
  ```
  using:
  ```
  GET https://api.github.com/repos/{owner}/{repo}/commits?per_page=100&page=1..5
  ```
- Extract at least these fields:
  - `sha`, `commit.message`, `commit.author.name`, `commit.author.date`

### 4. Save Outputs (5–10 min)
- Write results to:
  - `data/issues.csv` (last 500 issues)  
  - `data/pull_requests.csv` (last 500 PRs)  
  - `data/commits.csv` (last 500 commits)  
- Make sure each file has clean, tabular columns.
- 
---

## Notes
- Use `per_page=100` and loop over 5 pages to collect 500 items.  
- Focus on correct fetching and saving.  


## Environment setup

```shell
conda env create --name bug-triaging-env --file=environment.yml
conda activate bug-triaging-env
```

## Scraper

To run the scraper execute:

```shell
python3 main.py
```




