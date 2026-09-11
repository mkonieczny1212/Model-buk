from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from model_buk.config import load_corner_v02_config
from model_buk.inference import attach_total_market_price, load_corner_engine, predict_fixture
from model_buk.live_fit import fit_live_corner_models
from model_buk.suite import load_live_corner_suite, predict_with_live_suite
from model_buk.v02_backtest import run_v02_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="model-buk", description="Model Buk research engine")
    sub = parser.add_subparsers(dest="command", required=True)
    backtest = sub.add_parser("backtest-corners-v02")
    backtest.add_argument("--data", default="data/processed/epl_total_corners_v01.csv.gz"); backtest.add_argument("--config", default="config/corners_v02.toml"); backtest.add_argument("--outdir", default="outputs"); backtest.add_argument("--modeldir", default="models")
    fit_live = sub.add_parser("fit-live-corners")
    fit_live.add_argument("--data", default="data/processed/epl_total_corners_v01.csv.gz"); fit_live.add_argument("--config", default="config/corners_v02.toml"); fit_live.add_argument("--eval-v01-meta", default="models/metadata.json"); fit_live.add_argument("--eval-v02-meta", default="models/corner_dual_v0_2_metadata.json"); fit_live.add_argument("--model-root", default="models")
    for name in ("predict-corners", "predict-corners-v02"):
        p=sub.add_parser(name); p.add_argument("--history", default="data/canonical/epl_matches_v01.csv.gz"); p.add_argument("--config", default="config/corners_v02.toml"); p.add_argument("--date", required=True); p.add_argument("--home", required=True); p.add_argument("--away", required=True); p.add_argument("--line", type=float, default=None); p.add_argument("--over-odds", type=float, default=None); p.add_argument("--under-odds", type=float, default=None); p.add_argument("--out", default=None)
        p.add_argument("--model-root", default="models") if name=="predict-corners" else p.add_argument("--modeldir", default="models")
    return parser


def _validate_market_triplet(line, over, under):
    supplied=[x is not None for x in (line,over,under)]
    if any(supplied) and not all(supplied): raise SystemExit("--line, --over-odds and --under-odds must be supplied together")
    return all(supplied)


def _write_and_print(payload_obj, out):
    payload=json.dumps(payload_obj,indent=2)
    if out:
        path=Path(out); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(payload,encoding="utf-8")
    print(payload)


def main() -> None:
    args=build_parser().parse_args(); cfg=load_corner_v02_config(args.config)
    if args.command=="backtest-corners-v02": print(json.dumps(run_v02_pipeline(args.data,cfg,args.outdir,args.modeldir),indent=2)); return
    if args.command=="fit-live-corners": print(json.dumps(fit_live_corner_models(args.data,cfg,eval_v01_metadata_path=args.eval_v01_meta,eval_v02_metadata_path=args.eval_v02_meta,model_root=args.model_root),indent=2)); return
    history=pd.read_csv(args.history)
    if args.command=="predict-corners":
        prediction=predict_with_live_suite(history,load_live_corner_suite(args.model_root),cfg,date=args.date,home_team=args.home,away_team=args.away)
        if _validate_market_triplet(args.line,args.over_odds,args.under_odds): prediction["market_check"]=attach_total_market_price({"total_markets":prediction["total_corners"]["markets"]},cfg,line=args.line,over_odds=args.over_odds,under_odds=args.under_odds)["market_check"]
    elif args.command=="predict-corners-v02":
        prediction=predict_fixture(history,load_corner_engine(args.modeldir),cfg,date=args.date,home_team=args.home,away_team=args.away)
        if _validate_market_triplet(args.line,args.over_odds,args.under_odds): prediction=attach_total_market_price(prediction,cfg,line=args.line,over_odds=args.over_odds,under_odds=args.under_odds)
    else: raise RuntimeError(f"Unknown command: {args.command}")
    _write_and_print(prediction,args.out)


if __name__ == "__main__": main()
