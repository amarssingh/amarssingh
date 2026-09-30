#!/usr/bin/env python3
"""Fetch real GitHub stats via the official GraphQL API -> data/stats.json.

Needs GITHUB_TOKEN (provided automatically inside GitHub Actions).
If the request fails, the previous data/stats.json is kept untouched, so the
profile never shows invented numbers and never breaks.
"""
import json, os, pathlib, sys, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = json.loads((ROOT / "config/profile.json").read_text())["username"]
OUT = ROOT / "data/stats.json"

QUERY = """
query($login:String!, $after:String) {
  user(login:$login) {
    followers { totalCount }
    following { totalCount }
    repositories(ownerAffiliations:OWNER, isFork:false, first:100, after:$after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

def gql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set; keeping existing stats.json"); return 0
    try:
        stars, after = 0, None
        while True:
            u = gql(token, {"login": USER, "after": after})
            repos = u["repositories"]
            stars += sum(n["stargazerCount"] for n in repos["nodes"])
            if not repos["pageInfo"]["hasNextPage"]:
                break
            after = repos["pageInfo"]["endCursor"]
        cal = u["contributionsCollection"]["contributionCalendar"]
        stats = {
            "repos": repos["totalCount"], "stars": stars,
            "followers": u["followers"]["totalCount"], "following": u["following"]["totalCount"],
            "contributions": cal["totalContributions"],
            "calendar": [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]],
            "first_day": cal["weeks"][0]["contributionDays"][0]["date"],
            "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        }
        OUT.write_text(json.dumps(stats))
        print("stats updated:", {k: v for k, v in stats.items() if k != "calendar"})
    except Exception as e:  # network / API / auth problems: keep last good data
        print("fetch failed, keeping previous stats:", e, file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
