import http.client
import json
import os
import time
import csv
from urllib.parse import urlencode
from dotenv import load_dotenv
import argparse
from pathlib import Path

load_dotenv()

GITHUB_API = 'api.github.com'
ENDPOINT = ''
JSON_OUT_DIR = ''
HEADERS = {}
CONNECTION = http.client.HTTPSConnection(GITHUB_API)

PER_PAGE = 100
MAX_PAGES = 5
DEFAULT_MAX_ITEMS = 500

# CLI flags
def parse_args():
    p = argparse.ArgumentParser(description="GitHub data collector for MSR tasks.")
    p.add_argument("--type", choices=["issues", "pull_requests", "commits"], default="issues",
                   help="Type of data to fetch: issues, pull_requests, or commits.")
    p.add_argument("--owner", default="lobehub", help="Repository owner. Default: lobehub.")
    p.add_argument("--repo", default="lobe-chat", help="Repository name. Default: lobe-chat.")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub Personal Access Token. Falls back to GITHUB_TOKEN env var.")
    p.add_argument("--outdir", default="data", help="Output directory for CSV files. Default: ./data.")
    return p.parse_args()

def fetch_pages(query) -> list:
    """
    Fetch 5 pages of items from Github API based on the query parameters.
    Returns a list of items.
    """
    all_items = []
    for page in range(1, MAX_PAGES+1):
        query['page'] = page
        CONNECTION.request('GET', ENDPOINT + urlencode(query), headers=HEADERS)
        ret_text = CONNECTION.getresponse().read().decode()

        page_items = json.loads(ret_text)
        all_items.extend(page_items)
        time.sleep(1)
    return all_items

def fetch_issues(owner, repo) -> bool:
    query = {'state': 'closed', 'per_page': 100}
    all_items = fetch_pages(query)
    
    os.makedirs(JSON_OUT_DIR, exist_ok=True)
    csv_file = os.path.join(JSON_OUT_DIR, 'issues.csv')
    fieldnames = ['id','number', 'title', 'state', 'created_at', 
    'closed_at', 'user_login', 'comments', 'labels', 'labels_count']

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for issue in all_items:
            writer.writerow({
                'id': issue['id'],
                'number': issue['number'],
                'title': issue['title'],
                'state': issue['state'],
                'created_at': issue['created_at'],
                'closed_at': issue['closed_at'],
                'user_login': issue['user']['login'],
                'comments': issue['comments'],
                'labels': ';'.join(label['name'] for label in issue['labels']),
                'labels_count': len(issue['labels'])
            })
            print("Downloaded issue " + str(issue['id']))
    return len(all_items) == 500

def fetch_pull_requests(owner, repo):
    query = {'state': 'all', 'per_page': 100}
    all_items = fetch_pages(query)

    os.makedirs(JSON_OUT_DIR, exist_ok=True)
    csv_file = os.path.join(JSON_OUT_DIR, 'pull_requests.csv')
    fieldnames = ['id', 'number', 'title', 'state', 'created_at', 'updated_at', 
    'closed_at', 'user_login', 'merged_at', 'draft']

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pr in all_items:
            writer.writerow({
                'id': pr['id'],
                'number': pr['number'],
                'title': pr['title'],
                'state': pr['state'],
                'created_at': pr['created_at'],
                'updated_at': pr['updated_at'],
                'closed_at': pr['closed_at'],
                'user_login': pr['user']['login'],
                'merged_at': pr['merged_at'],
                'draft': pr['draft']
            })
            print("Downloaded pull request " + str(pr['id']))
    return len(all_items) == 500

def fetch_commits(owner, repo):
    query = {'per_page': 100}
    all_items = fetch_pages(query)

    os.makedirs(JSON_OUT_DIR, exist_ok=True)
    csv_file = os.path.join(JSON_OUT_DIR, 'commits.csv')
    fieldnames = ['sha', 'commit.message', 'commit.author.name', 'commit.author.date']

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for commit in all_items:
            writer.writerow({
                'sha': commit['sha'],
                'commit.message': commit['commit']['message'],
                'commit.author.name': commit['commit']['author']['name'],
                'commit.author.date': commit['commit']['author']['date']
            })
            print("Downloaded commit " + str(commit['sha']))
    return len(all_items) == 500

def main():
    global ENDPOINT, JSON_OUT_DIR, HEADERS, CONNECTION   # make assignments affect globals
    args = parse_args()
    owner, repo, TOKEN = args.owner, args.repo, args.token
    JSON_OUT_DIR = Path(args.outdir)
    HEADERS = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'wm-2024-ai4se',
               'Authorization': 'Bearer ' + TOKEN,
               'X-GitHub-Api-Version': '2022-11-28'}
    if args.type == 'issues':
        ENDPOINT = '/repos/'+owner+'/'+repo+'/issues?'   
        fetch_issues(owner, repo)            
    elif args.type == 'pull_requests':
        ENDPOINT = '/repos/'+owner+'/'+repo+'/pulls?'
        fetch_pull_requests(owner, repo)
    else:
        ENDPOINT = '/repos/'+owner+'/'+repo+'/commits?'
        fetch_commits(owner, repo)


if __name__ == '__main__':
    main()
