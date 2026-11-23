#!/usr/bin/env python3
"""Generate a self-hosted activity SVG using GitHub GraphQL. Standard library only."""
import argparse
import datetime as dt
from html import escape
import json
import os
from pathlib import Path
import re
import urllib.request

QUERY = '''query($login: String!) {
  user(login: $login) {
    login
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    followers { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}'''

def fetch(login):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise SystemExit('GITHUB_TOKEN is required. Run this script through the supplied workflow.')
    payload = json.dumps({'query': QUERY, 'variables': {'login': login}}).encode()
    request = urllib.request.Request('https://api.github.com/graphql', data=payload, headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'github-profile-activity-renderer',
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('errors') or not result.get('data', {}).get('user'):
        raise SystemExit('GitHub did not return valid profile data; existing SVG was preserved.')
    return result['data']['user']

def render(user):
    calendar = user['contributionsCollection']['contributionCalendar']
    weeks = calendar['weeks']
    dates = [d['date'] for w in weeks for d in w['contributionDays']]
    if not dates:
        raise ValueError('No contribution calendar returned')
    # Each cell and metric is sourced from GitHub, not an illustrative score.
    start, end = min(dates), max(dates)
    total = int(calendar['totalContributions'])
    repos = int(user['repositories']['totalCount'])
    followers = int(user['followers']['totalCount'])
    pieces = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="316" viewBox="0 0 1000 316" role="img">
<title>GitHub contribution activity</title><style>text{font-family:ui-monospace,Consolas,monospace}.sweep{animation:sweep 9s linear infinite}@keyframes sweep{from{transform:translateX(0)}to{transform:translateX(950px)}}@media(prefers-reduced-motion:reduce){.sweep{animation:none;opacity:0}}</style>
<defs><clipPath id="calendar"><rect x="28" y="142" width="944" height="116"/></clipPath></defs>
<rect x="1" y="1" width="998" height="314" rx="12" fill="#080e1b" stroke="#25354d"/>
<text x="28" y="34" fill="#51e3d4" font-size="12">06 / GITHUB ACTIVITY</text>
''']
    pieces.append(f'<text x="972" y="34" text-anchor="end" fill="#8fa3c1" font-size="10">SYNCED {dt.datetime.now(dt.timezone.utc):%Y-%m-%d} UTC</text>')
    for x, value, label in [(28,total,'CONTRIBUTIONS IN PERIOD'),(360,repos,'PUBLIC REPOSITORIES'),(692,followers,'FOLLOWERS')]:
        pieces.append(f'<text x="{x}" y="87" fill="#e4edfc" font-size="32">{value:,}</text><text x="{x}" y="113" fill="#8fa3c1" font-size="10">{label}</text>')
    max_count = max(1, max(int(d['contributionCount']) for w in weeks for d in w['contributionDays']))
    colors = ['#142237','#184855','#217d81','#36b4ad','#51e3d4']
    step = min(17.5, 944 / max(1,len(weeks)))
    for x, week in enumerate(weeks):
        for day in week['contributionDays']:
            n = int(day['contributionCount'])
            level = 0 if n == 0 else min(4,1+int(3*n/max_count))
            pieces.append(f'<rect x="{28+x*step:.1f}" y="{142+int(day["weekday"])*16}" width="{step-3:.1f}" height="13" rx="2" fill="{colors[level]}"><title>{escape(day["date"])}: {n} contributions</title></rect>')
    pieces.append('<g clip-path="url(#calendar)"><rect class="sweep" x="28" y="142" width="2" height="112" fill="#c4b5fd" opacity=".65"/></g>')
    pieces.append(f'<text x="28" y="285" fill="#8fa3c1" font-size="11">{escape(user["login"])} · {start} → {end} · GitHub-visible contribution data</text></svg>')
    return ''.join(pieces)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default=os.environ.get('PROFILE_USER','dogukanc760'))
    parser.add_argument('--output', default='assets/activity.svg')
    parser.add_argument('--fixture', help='Offline test fixture; not used by the workflow')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]+', args.user):
        raise SystemExit('Invalid GitHub username')
    user = json.loads(Path(args.fixture).read_text()) if args.fixture else fetch(args.user)
    svg = render(user)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.svg.tmp')
    temp.write_text(svg)
    temp.replace(target)
    print('Activity SVG updated successfully.')

if __name__ == '__main__':
    main()
