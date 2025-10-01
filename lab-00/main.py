import http.client
import os
import csv
from dotenv import load_dotenv
import re
import sys
from pathlib import Path
import subprocess

from github import Github
from github import Auth
from pydriller import Repository
import javalang

def search_top_repos(Token, PERMISSIVE, number=10, min_stars=100):
    """
    search top repositories on GitHub based on stars and licenses
        input: number of repositories to return, minimum stars of repo
        return a list of repository objects
            owner: repo.owner.login
            name: repo.name
            license: repo.license.spdx_id
    """
    print(f"Searching top {number} Java repositories with more than {min_stars} stars and permissive licenses...")

    auth = Auth.Token(Token)
    g = Github(auth=auth)
    query = f"language:java stars:>{min_stars}"

    repos = g.search_repositories(query=query, sort='stars', order='desc')
    results = []
    for repo in repos:
        # if spdx_id exists
        spdx_id = repo.license.spdx_id if (repo.license and repo.license.spdx_id not in (None, "NOASSERTION")) else None
        if not verify_license(spdx_id, PERMISSIVE):
            continue
        results.append(repo)
        print(f"{repo.owner.login}/{repo.name} (License: {spdx_id})")
        if len(results) >= number:
            break
    print("Total results: ", len(results), "\n")
    return results

def verify_license(license, PERMISSIVE) -> bool:
    """
    verify if license is permissive
        input license: spdx_id of the license
        return True if license is permissive, False if license is incampatible or missing
    """
    if license is None:
        return False
    return license in PERMISSIVE

def get_commit(owner, repo, branch):
    """
    get repo's content
        input: owner, repo name, branch
        return latest commit hash
    """
    latest_commit = next(Repository('https://github.com/' + owner + '/' + repo, 
                    only_in_branch=branch, 
                    order='reverse'). #date from newest to oldest
                    traverse_commits())
    print(f"Latest commit on {repo}/{owner} ({branch}): {latest_commit.hash}")
    return latest_commit.hash

def download_repo(owner, repo):
    """
    download repo using git clone
        input: owner, repo name
        return target directory path
    """
    target_dir = Path(f"{owner}_{repo}")
    if not target_dir.exists():
        subprocess.run(['git', 'clone', "--depth", "1",
            f"https://github.com/{owner}/{repo}.git",
            str(target_dir)
        ], check=True)
    return target_dir

def delete_repo(target_dir):
    """
    delete the downloaded repo
        input: target directory path
        return: None
    """
    if target_dir.exists():
        subprocess.run(['rm', '-rf', str(target_dir)], check=True)

def get_java_files(repo_path):
    """
    get all java files in the repo
        input: repo path
        return a list of java file paths of the repo
    """
    return list(Path(repo_path).rglob("*.java"))

def remove_comments(code):
    """
    remove comments from java code
        input: java code as a string
        return code without comments
    """
    code = re.compile(r"/\*.*?\*/", re.DOTALL).sub("", code)
    code = re.compile(r"//.*?$", re.MULTILINE).sub("", code)
    return code

def remove_blank(code):
    """
    remove all blank spaces(blanks, tabs, newlines)
        input: code as a string
        return code without blank spaces
    """
    return re.sub(r"\s+", " ", code).strip()

def tokenize_code(code):
    """
    tokenize code using regex
        input: code as a string
        return a list of tokens
    """
    return  re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\d+|".*?"|\'.*?\'|==|!=|<=|>=|&&|\|\||[^\s]', code)

def extract_methods(java_path, repos):
    """
    extract methods 
        javalang to get method info; add with java_path and repos info;
        input: java file path, repos info
        return a list of methods
    """
    # read java file
    source = Path(java_path).read_text(encoding="utf-8", errors="replace")
    source_bytes = source.encode("utf8")
    # verify if file is valid
    try:
        tree = javalang.parse.parse(source_bytes)
        results = []
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            method_name = node.name
            start_line = node.position.line if node.position else None
            end_line = start_line
            if node.body:
                l = node.body[-1]
                if hasattr(l, 'position') and l.position:
                    end_line = l.position.line
                else:
                    end_line = start_line + len(body)
            original_code = remove_blank(remove_comments("\n".join(source.splitlines()[start_line - 1:end_line]))) if start_line and    end_line else None
            params = ', '.join([f"{param.type.name} {param.name}" for param in node.parameters]) 
            signature = f"{node.return_type.name if node.return_type else 'void'} {method_name}({params})"
            code_tokens = tokenize_code(original_code) if original_code else []
            data = {
                "repo_name": repos["repo_name"],
                "repo_url": repos["repo_url"],
                "commit_sha": repos["commit_sha"],
                "file_path": java_path,
                "method_name": method_name,
                "start_line": start_line,
                "end_line": end_line,
                "signature": signature,
                "original_code": original_code,
                "code_tokens": code_tokens
            }
            results.append(data)
        return results
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as e:
        return []

def write_file(methods, output_file, index):
    """
    write mined java methods to CSV file
        input: dataset_split (train/val/test), methods info, output file path
        return: None
    """
    dataset_split = ["train", "eval", "test"]
    indexs = [20000, 25000, 30000]
    num = 0
    with open(output_file, "a", newline='', encoding='utf-8') as csvfile:
        fieldnames = ["dataset_split", "repo_name", "repo_url", "commit_sha", "file_path", "method_name", "start_line", "end_line", "signature", "original_code", "code_tokens"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for idx in range(len(methods)):
            method = methods[idx]
            if idx+index < indexs[0]:
                num = 0
            elif idx+index < indexs[1]:
                num = 1
            elif idx+index < indexs[2]:
                num = 2
            else:
                return idx+index
            row = {
                "dataset_split": dataset_split[num],
                "repo_name": method["repo_name"],
                "repo_url": method["repo_url"],
                "commit_sha": method["commit_sha"],
                "file_path": method["file_path"],
                "method_name": method["method_name"],
                "start_line": method["start_line"],
                "end_line": method["end_line"],
                "signature": method["signature"],
                "original_code": method["original_code"],
                "code_tokens": method["code_tokens"]
            }
            writer.writerow(row)
        print("Successfully wrote")
        return len(methods)+index

def main():
    load_dotenv()
    Token = os.getenv("GITHUB_TOKEN")
    if not Token:
        raise SystemExit("Error: Please set the GITHUB_TOKEN environment variable.")

    PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Unlicense", "CC0-1.0"}
    train_size = 20000
    eval_size = 5000
    test_size = 5000
    repos = search_top_repos(Token, PERMISSIVE)
    index = 0
    for repo in repos:
        print(f"Processing repository: {repo.owner.login}/{repo.name}")
        # Download the repo
        target_dir = download_repo(repo.owner.login, repo.name)  
        print(f"Target directory: {target_dir}")
        # get commit in default branch
        commit_sha = get_commit(repo.owner.login, repo.name, repo.default_branch)  
        java_files = get_java_files(target_dir)
        repos = {
            "repo_name": f"{repo.owner.login}/{repo.name}",
            "repo_url": repo.html_url,
            "commit_sha": commit_sha,
        }
        methods = []
        for java_file in java_files:
            method_info = extract_methods(java_file, repos)
            if method_info:
                methods.extend(method_info)
        print(f"writing {len(methods)} methods from {len(java_files)} Java files of {repo.owner.login}/{repo.name}.")

        index = write_file(methods, f"java_methods.csv", index)
        # Clean up the cloned repository
        delete_repo(target_dir)  
        if index >= train_size + eval_size + test_size:
            print("Reached the desired dataset size. Stopping further processing.")
            return
        print(f"Finished processing repository: {repo.owner.login}/{repo.name}\n")

if __name__ == "__main__":
    main()