"""Refresh explicitly selected public Understat seasons, with source manifest.

Usage: python scripts/refresh_understat.py --seasons 2021 2026
Each league-season costs one HTTP request. Existing seasons remain intact if
the source is unavailable or fails validation. Retrain after updating history.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from model_buk.security import configure_system_tls, safe_error

ROOT = Path(__file__).resolve().parents[1]
LEAGUES = {'EPL': ('eng', 'ENG-Premier League', 1), 'La_liga': ('esp', 'ESP-La Liga', 4),
           'Bundesliga': ('ger', 'GER-Bundesliga', 3), 'Serie_A': ('ita', 'ITA-Serie A', 2), 'Ligue_1': ('fra', 'FRA-Ligue 1', 5)}


def canonical(data, league, season):
    _, name, league_id = LEAGUES[league]
    teams = data.get('teams') or {}
    lookup = {(str(t['id']), r['date']): r for t in teams.values() for r in t.get('history', [])}
    rows = []
    now = pd.Timestamp.now(tz='UTC')
    for m in data.get('dates', []):
        if not m.get('isResult') or pd.to_datetime(m['datetime'], utc=True) >= now:
            continue
        row = {'league': name, 'season': int(f'{season%100:02}{(season+1)%100:02}'), 'league_id': league_id,
               'season_id': season, 'game_id': int(m['id']), 'date': m['datetime'], 'game': f"{m['datetime'][:10]} {m['h']['title']}-{m['a']['title']}"}
        for side, key in (('home', 'h'), ('away', 'a')):
            team = m[key]
            stats = lookup.get((str(team['id']), m['datetime']), {})
            ppda = stats.get('ppda') or {}
            fields = {'team_id': int(team['id']), 'team': team['title'], 'team_code': team.get('short_title'),
                      'goals': float(m['goals'][key]), 'xg': float(m['xG'][key]), 'np_xg': stats.get('npxG'),
                      'np_xg_difference': stats.get('npxGD'), 'ppda': ppda.get('att', 0)/ppda['def'] if ppda.get('def') else None,
                      'deep_completions': stats.get('deep'), 'expected_points': stats.get('xpts'), 'points': stats.get('pts')}
            row.update({side+'_'+k: v for k,v in fields.items()})
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty or frame.game_id.duplicated().any() or frame[['home_goals','away_goals','home_xg','away_xg']].isna().any().any():
        raise ValueError('Empty or invalid completed-match data')
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seasons', nargs='+', type=int, required=True)
    args = parser.parse_args()
    configure_system_tls()
    manifest = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sources': []}
    for league, (prefix, _, _) in LEAGUES.items():
        path = ROOT/'data/understat'/f'{prefix}_team_match_stats.csv'
        old = pd.read_csv(path) if path.exists() else pd.DataFrame()
        for season in args.seasons:
            url = f'https://understat.com/getLeagueData/{league}/{season}'
            record = {'url': url, 'season': season, 'league': league}
            try:
                response = requests.get(url, headers={'X-Requested-With':'XMLHttpRequest', 'Referer':f'https://understat.com/league/{league}/{season}'}, timeout=30)
                response.raise_for_status()
                fresh = canonical(response.json(), league, season)
                record.update(matches=len(fresh), sha256=hashlib.sha256(response.content).hexdigest(), through=str(fresh.date.max()))
                old = pd.concat([old, fresh], ignore_index=True).drop_duplicates('game_id',keep='last').sort_values('date')
            except Exception as exc:
                record['error'] = safe_error(exc)
            manifest['sources'].append(record)
            print(json.dumps(record), flush=True)
        if not old.empty:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.csv.tmp')
            old.to_csv(temp,index=False)
            temp.replace(path)
    dest = ROOT/'data/understat/source_manifest.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__ == '__main__': main()
