"""
Fetches total commit contribution counts for the last 30 / 60 / 90 / 180 / 365
days using the GitHub GraphQL API, then writes them into README.md between
the <!--COMMITS:START--> and <!--COMMITS:END--> markers.

Requires env vars:
  GH_TOKEN     - a token with 'read:user' scope (the default GITHUB_TOKEN
                 in Actions works fine for the authenticated user's own stats)
  GH_USERNAME  - your GitHub username
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

GH_TOKEN = os.environ["GH_TOKEN"]
GH_USERNAME = os.environ["GH_USERNAME"]
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"bearer {GH_TOKEN}"}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""


def commits_in_last_days(days: int) -> int:
    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=days)
    variables = {
        "login": GH_USERNAME,
        "from": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        print(data["errors"], file=sys.stderr)
        resp.raise_for_status()
    collection = data["data"]["user"]["contributionsCollection"]
    # includes contributions to private repos you're a member of
    return collection["totalCommitContributions"] + collection["restrictedContributionsCount"]


def main():
    windows = {
        "30 days": 30,
        "60 days": 60,
        "90 days": 90,
        "6 months": 182,
        "1 year": 365,
    }

    counts = {label: commits_in_last_days(days) for label, days in windows.items()}
    print("Commit counts:", counts)

    row = (
        f"| {counts['30 days']} | {counts['60 days']} | {counts['90 days']} "
        f"| {counts['6 months']} | {counts['1 year']} |"
    )

    table = (
        "<!--COMMITS:START-->\n"
        "| ⏱️ Last 30 Days | ⏱️ Last 60 Days | ⏱️ Last 90 Days | 🗓️ Last 6 Months | 🗓️ Last 1 Year |\n"
        "|:---:|:---:|:---:|:---:|:---:|\n"
        f"{row}\n"
        "<!--COMMITS:END-->"
    )

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r"<!--COMMITS:START-->.*?<!--COMMITS:END-->",
        table,
        content,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    main()
