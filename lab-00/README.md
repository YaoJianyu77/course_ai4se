# Java Method Mining (AI4SE Lab‑00)

This lab collects Java methods from popular, permissively licensed GitHub repositories to build a dataset with train / eval / test(20k / 5k / 5k methods).  
The script `main.py` automates:
1. Repository discovery (by stars + license filtering)
2. Cloning and commit pinning
3. Java file enumeration
4. Method AST parsing (via `javalang`)
5. Lightweight code normalization, tokenization, and CSV export

## Goals
- Build a reproducible Java method corpus.
- Ensure each row records provenance (repository name, URL, commit SHA, file path).
- Provide a consistent tokenization for downstream ML tasks.
- Respect license constraints (only permissive SPDX IDs).

## Current Features
| Feature | Status | Notes |
|---------|--------|-------|
| Repo search by stars + language | ✅ | Uses GitHub Search API |
| License filtering (MIT / Apache-2.0 / BSD / etc.) | ✅ | See `PERMISSIVE` set |
| Shallow clone (depth=1) | ✅ | Fast acquisition |
| Commit SHA capture | ✅ | Uses PyDriller on default branch |
| Java file discovery (recursive) | ✅ | `Path.rglob("*.java")` |
| Method extraction via `javalang` | ✅ | AST-based (may miss malformed/new-syntax files) |
| Comment stripping | ✅ | Regex-based (may over-strip block strings) |
| Whitespace normalization | ✅ | Collapses to single spaces |
| Tokenization (regex) | ✅ | Basic identifiers, literals, operators |
| CSV export with incremental split labeling | ✅ | Header currently re-written each append (see issues) |
| Error handling for parse failures | Partial | Catches `JavaSyntaxError` / `LexerError` (silently skips) |


## Extracted Fields
| Column | Description |
|--------|-------------|
| `dataset_split` | train / eval / test (assigned by index) |
| `repo_name` | owner/repo |
| `repo_url` | GitHub repository HTML URL |
| `commit_sha` | Commit hash (default branch head at mining time) |
| `file_path` | Local path to the Java source file (within cloned repo folder) |
| `method_name` | Simple method identifier |
| `start_line` | Starting line number (from `javalang` AST) |
| `end_line` | Heuristic end line (see known issues) |
| `signature` | Return type + name + parameter list |
| `original_code` | Method body (comments stripped, whitespace collapsed) |
| `code_tokens` | Token list (Python list serialized via CSV default conversion) |

## Pipeline Overview

1. **Search Repositories**  
   GitHub API query: `language:java stars:>100`, descending by stars.  
   Filter to permissive licenses (`PERMISSIVE` set).
   Top 10 repos selected.

2. **Clone Repository**  
   `git clone --depth 1` for speed.

3. **Resolve Commit SHA**  
   PyDriller iterates the default branch; the first (newest) commit is recorded.

4. **Enumerate Java Files**  
   Recursively find `*.java`.

5. **Parse & Extract Methods**  
   For each file:
   - Parse via `javalang.parse.parse`.
   - Iterate `MethodDeclaration` nodes.
   - Derive start/end lines & parameters.
   - Normalize method code (remove comments, collapse whitespace).
   - Tokenize.

6. **Aggregate & Write**  
   Append method metadata to `java_methods.csv`; assign split.

7. **Cleanup**  
   Delete the cloned repository directory to conserve space.

---

## Installation 

Create a `.env` file:
```
GITHUB_TOKEN=ghp_your_token_here
```

Install commands:
```bash
pip install PyDriller PyGithub python-dotenv javalang
```


## Running the Script

```bash
python main.py
```

Output CSV: `java_methods.csv` (created in the working directory).

## Tokenization & Normalization

Current regex:
```
[A-Za-z_][A-Za-z0-9_]* | \d+ | ".*?" | '.*?' | == | != | <= | >= | && | \|\| | [^\s]
```