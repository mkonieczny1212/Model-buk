"""Chronological offline check of live count model (not provider-shift approval).

Feeds only previously completed domestic matches through the same rate estimator
used by the live service. UEFA cross-league calibration is explicitly out of scope.
"""
from collections import defaultdict, deque
from pathlib import Path
import json
import numpy as np
import pandas as pd
from model_buk.live_model import _rate
from model_buk.multimarket import load_multileague_history, METRICS, MetricEstimate, _convolved_over

ROOT=Path(__file__).resolve().parents[1]


def main():
    history=load_multileague_history(ROOT/'data/multileague/europe16_matches_v05.csv.gz')
    boundary=pd.Timestamp('2024-07-01')
    lines={'goals':2.5,'corners':9.5,'shots':23.5,'sot':7.5,'cards':4.5}
    evaluations=defaultdict(list)
    states=defaultdict(lambda:deque(maxlen=20))
    baseline={}
    for division, group in history[history.MatchDate<boundary].groupby('Division'):
        for metric,(h,a) in METRICS.items():
            observed=group.dropna(subset=[h,a])
            if len(observed):baseline[(division,metric)]=float((observed[h]+observed[a]>lines[metric]).mean())
    eligible=0
    for day, fixtures in history.groupby(history.MatchDate.dt.normalize(),sort=True):
        # Freeze every team state for the full day; update only after prediction.
        for _,match in fixtures.iterrows():
            if day<boundary:continue
            eligible+=1
            if eligible%20:continue  # Fixed sampling rule, independent of outcomes.
            home=list(states[(match.Division,match.HomeTeam)])
            away=list(states[(match.Division,match.AwayTeam)])
            when=pd.Timestamp(day,tz='UTC')
            for metric,(hcol,acol) in METRICS.items():
                if pd.isna(match[hcol]) or pd.isna(match[acol]) or (match.Division,metric) not in baseline:continue
                h=_rate(home,away,[],[],metric,when,'home')
                a=_rate(away,home,[],[],metric,when,'away')
                if not h['available'] or not a['available']:continue
                est=MetricEstimate(metric,h['mean'],a['mean'],h['alpha'],a['alpha'],0,0,0,0,0,0,0,0,'evaluation')
                p=_convolved_over(est,lines[metric]);y=float(match[hcol]+match[acol]>lines[metric])
                evaluations[metric].append((p,y,baseline[(match.Division,metric)]))
        for _,match in fixtures.iterrows():
            for side,team in (('home',match.HomeTeam),('away',match.AwayTeam)):
                row={'date':str(day),'venue':side}
                for metric,(h,a) in METRICS.items():
                    row[metric+'_for']=match[h if side=='home' else a]
                    row[metric+'_against']=match[a if side=='home' else h]
                states[(match.Division,team)].append(row)
    report={'model':'live-gamma-poisson-v0.7','split':'test >= 2024-07-01; constant baseline estimated before split',
            'selection':'Every twentieth chronological test fixture, before inspecting its result',
            'validation_status':'research; historical domestic simulation is not validation of UEFA or API data', 'metrics':{}}
    for metric,rows in evaluations.items():
        p,y,b=np.array(rows).T
        report['metrics'][metric]={'n':len(rows),'line':lines[metric], 'brier':float(np.mean((p-y)**2)), 'constant_baseline_brier':float(np.mean((b-y)**2)),
                                   'log_loss':float(-np.mean(y*np.log(np.clip(p,1e-8,1))+(1-y)*np.log(np.clip(1-p,1e-8,1))))}
    out=ROOT/'models/live_v07';out.mkdir(parents=True,exist_ok=True)
    (out/'evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
