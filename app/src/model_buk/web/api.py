from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from model_buk.web.service import PredictionService, ServicePaths
from model_buk.web.service_v062 import MatchAnalysisService
from model_buk.web.storage import PredictionStore
from model_buk.security import safe_error
from model_buk.settlement import MaintenanceWorker, SettlementEngine, validation_report


class CornerPredictionRequest(BaseModel):
    date: str = Field(description="Fixture date/time")
    home_team: str
    away_team: str
    line: float | None = None
    over_odds: float | None = Field(default=None, gt=1.0)
    under_odds: float | None = Field(default=None, gt=1.0)
    persist: bool = True


class ManualAnalysisRequest(BaseModel):
    league_code: str
    date: str
    home_team: str
    away_team: str
    persist: bool = True


class ScanRequest(BaseModel):
    date: str
    league_codes: list[str] | None = None
    max_fixtures: int = Field(default=5, ge=1, le=10)
    deep: bool = False
    persist: bool = True


def _paths() -> ServicePaths:
    return ServicePaths(
        history=Path(os.getenv("MODEL_BUK_HISTORY", "data/canonical/epl_matches_v01.csv.gz")),
        model_root=Path(os.getenv("MODEL_BUK_MODEL_ROOT", "models")),
        config=Path(os.getenv("MODEL_BUK_CONFIG", "config/corners_v02.toml")),
        multileague_history=Path(os.getenv("MODEL_BUK_MULTILEAGUE_HISTORY", "data/multileague/europe16_matches_v05.csv.gz")),
        stadiums=Path(os.getenv("MODEL_BUK_STADIUMS", "data/stadiums_europe.json")),
        understat=Path(os.getenv("MODEL_BUK_UNDERSTAT", "data/understat")),
        goal_model=Path(os.getenv("MODEL_BUK_GOAL_MODEL", "models/goal_v06")),
    )


def _default_service() -> PredictionService:
    return PredictionService(_paths())


def _default_analysis_service() -> MatchAnalysisService:
    return MatchAnalysisService(_paths())


def create_app(
    service: PredictionService | Any | None = None,
    analysis_service: MatchAnalysisService | Any | None = None,
    store: PredictionStore | Any | None = None,
    static_dir: str | Path | None = None,
) -> FastAPI:
    production_startup = service is None and analysis_service is None
    legacy_service = service or _default_service()
    # Existing tests can inject only the legacy service. New production startup
    # creates the v0.6 analysis orchestrator automatically.
    if analysis_service is None and service is None:
        analysis_service = _default_analysis_service()
    store = store or PredictionStore(os.getenv("MODEL_BUK_DB", "runtime/model_buk.sqlite3"))
    static_path = Path(static_dir or Path(__file__).with_name("static"))
    settlement_engine = None
    if analysis_service is not None and getattr(analysis_service, "provider", None) is not None:
        settlement_engine = SettlementEngine(store, analysis_service.provider)
    maintenance_worker = (
        MaintenanceWorker(
            settlement_engine,
            interval_seconds=int(os.getenv("MODEL_BUK_MAINTENANCE_INTERVAL", "900")),
        )
        if settlement_engine is not None
        and production_startup
        and os.getenv("MODEL_BUK_AUTO_MAINTENANCE", "1") == "1"
        else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if maintenance_worker is not None:
            maintenance_worker.start()
        try:
            yield
        finally:
            if maintenance_worker is not None:
                maintenance_worker.stop()

    app = FastAPI(
        title="Model Buk API",
        version="0.9.1",
        description="Multi-league, multi-market football probability + current-context research engine.",
        lifespan=lifespan,
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        if analysis_service is not None:
            try:
                state = analysis_service.status()
                if state.get("status") in {"degraded", "unavailable", "error"} or state.get("degraded"):
                    return {"status": "degraded"}
            except Exception:
                return {"status": "degraded"}
        return {"status": "ok"}

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        try:
            if analysis_service is not None:
                return analysis_service.status()
            return legacy_service.status()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/catalog/leagues")
    def leagues() -> dict[str, Any]:
        if analysis_service is None:
            return {"leagues": []}
        try:
            return {"leagues": analysis_service.leagues()}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/teams")
    def teams(league: str | None = None) -> dict[str, list[str]]:
        try:
            if league and analysis_service is not None:
                return {"teams": analysis_service.teams(league)}
            return {"teams": legacy_service.teams()}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/fixtures")
    def fixtures(date: str, league: list[str] | None = Query(default=None)) -> dict[str, Any]:
        if league is not None and not any(league):
            return {"mode": "live", "fixtures": [], "message": "Nie wybrano żadnej ligi."}
        if analysis_service is None:
            return {"mode": "manual", "fixtures": [], "message": "Live fixture service unavailable in this test mode."}
        try:
            return analysis_service.fixtures(date, league or None)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.post("/api/analyze/manual")
    def analyze_manual(request: ManualAnalysisRequest) -> dict[str, Any]:
        if analysis_service is None:
            raise HTTPException(status_code=503, detail="v0.6 analysis service unavailable")
        try:
            payload = analysis_service.analyze_manual(
                request.league_code,
                request.date,
                request.home_team,
                request.away_team,
            )
            if request.persist:
                payload["prediction_id"] = store.save(payload)
            return payload
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.post("/api/analyze/fixture/{fixture_id}")
    def analyze_fixture(fixture_id: int, deep: bool = True, persist: bool = True) -> dict[str, Any]:
        if analysis_service is None:
            raise HTTPException(status_code=503, detail="v0.6 analysis service unavailable")
        try:
            payload = analysis_service.analyze_fixture(fixture_id, deep=deep)
            normalized_odds = payload.get("normalized_odds") or []
            if persist and normalized_odds:
                payload["odds_snapshots_saved"] = store.save_odds(fixture_id, normalized_odds)
            if persist:
                payload["prediction_id"] = store.save(payload)
            return payload
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.post("/api/scan")
    def scan(request: ScanRequest) -> dict[str, Any]:
        if analysis_service is None:
            raise HTTPException(status_code=503, detail="v0.9 scan service unavailable")
        if request.league_codes is not None and not any(request.league_codes):
            raise HTTPException(status_code=422, detail="Wybierz co najmniej jedną ligę.")
        try:
            payload = analysis_service.scan_fixtures(
                request.date,
                request.league_codes,
                max_fixtures=request.max_fixtures,
                deep=request.deep,
            )
            if request.persist:
                payload["scan_id"] = store.save_scan(payload)
            return payload
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/scans")
    def scans(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return {"scans": store.recent_scans(limit)}

    @app.post("/api/maintenance/capture-closing")
    def capture_closing(horizon_minutes: int = Query(default=180, ge=15, le=720)) -> dict[str, Any]:
        if settlement_engine is None:
            raise HTTPException(status_code=503, detail="Live settlement provider unavailable")
        try:
            return settlement_engine.capture_closing_odds(horizon_minutes=horizon_minutes)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.post("/api/maintenance/reconcile")
    def reconcile(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
        if settlement_engine is None:
            raise HTTPException(status_code=503, detail="Live settlement provider unavailable")
        try:
            return settlement_engine.reconcile(limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.post("/api/maintenance/run")
    def maintenance_run() -> dict[str, Any]:
        if settlement_engine is None:
            raise HTTPException(status_code=503, detail="Live settlement provider unavailable")
        try:
            if maintenance_worker is not None:
                return maintenance_worker.run_once()
            return {
                "at": datetime.now(timezone.utc).isoformat(),
                "captured": settlement_engine.capture_closing_odds(),
                "settled": settlement_engine.reconcile(),
            }
        except Exception as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/maintenance/status")
    def maintenance_status() -> dict[str, Any]:
        return {
            "automatic": maintenance_worker is not None,
            "interval_seconds": maintenance_worker.interval_seconds if maintenance_worker else None,
            "last_result": maintenance_worker.last_result if maintenance_worker else None,
        }

    @app.get("/api/validation/report")
    def report(min_sample: int = Query(default=200, ge=30, le=5000)) -> dict[str, Any]:
        return validation_report(store, min_sample=min_sample)

    # Legacy v0.4 corner endpoint remains available for reproducibility.
    @app.post("/api/predict/corners")
    def predict_corners(request: CornerPredictionRequest) -> dict[str, Any]:
        try:
            payload = legacy_service.predict(**request.model_dump(exclude={"persist"}))
            if request.persist:
                payload["prediction_id"] = store.save(payload)
            return payload
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=safe_error(exc)) from exc

    @app.get("/api/predictions")
    def predictions(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
        items = store.recent(limit)
        return {
            "predictions": [
                {
                    "id": item.id,
                    "created_at": item.created_at,
                    "fixture_date": item.fixture_date,
                    "home_team": item.home_team,
                    "away_team": item.away_team,
                    "model_version": item.model_version,
                    "decision": item.decision,
                    "payload": item.payload,
                }
                for item in items
            ]
        }

    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_path / "index.html")

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "model_buk.web.api:app",
        host=os.getenv("MODEL_BUK_HOST", "127.0.0.1"),
        port=int(os.getenv("MODEL_BUK_PORT", "8000")),
        reload=os.getenv("MODEL_BUK_RELOAD", "0") == "1",
    )


if __name__ == "__main__":
    run()
