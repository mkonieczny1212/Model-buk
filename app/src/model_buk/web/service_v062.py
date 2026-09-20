from __future__ import annotations

from typing import Any

from model_buk.catalog import LEAGUES
from model_buk.secondary_providers import FootyStatsClient, SportmonksClient
from model_buk.security import safe_error
from model_buk.web.service import MatchAnalysisService as BaseMatchAnalysisService


class MatchAnalysisService(BaseMatchAnalysisService):
    """v0.6.2 decorator around the v0.6.1 analysis service.

    Secondary providers are deliberately reconciliation/context sources only.
    Their fields do not change P_model until point-in-time historical backfill,
    chronological OOS and ablation gates are complete.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.footystats = FootyStatsClient()
        self.sportmonks = SportmonksClient()

    def status(self) -> dict[str, Any]:
        payload = super().status()
        payload["app_version"] = "0.8.0"
        payload["secondary_providers"] = {
            "footystats": self.footystats.status(),
            "sportmonks": self.sportmonks.status(),
        }
        return payload

    def teams(self, league_code: str) -> list[str]:
        # A connected current provider is authoritative for the current-season
        # roster. If that lookup fails, returning [] is safer than reintroducing
        # relegated/historical clubs into a selector labelled as current.
        if self.provider.connected:
            try:
                return [row["name"] for row in self.provider.teams_for_league(league_code)]
            except Exception:
                return []
        return self.multimarket.teams(league_code)

    def analyze_fixture(self, fixture_id: int, deep: bool = True) -> dict[str, Any]:
        analysis = super().analyze_fixture(fixture_id, deep=deep)
        fixture = analysis.get("fixture") or {}
        league = analysis.get("league") or {}
        league_code = league.get("code")
        home_name = fixture.get("home_team") or ""
        away_name = fixture.get("away_team") or ""

        current = analysis.setdefault("current_context", {})
        # Some development builds already decorate the base service directly.
        # In that case do not duplicate secondary-provider requests.
        if current.get("secondary_reconciliation"):
            return analysis
        secondary: dict[str, Any] = {}
        if deep and self.footystats.connected and league_code in LEAGUES:
            try:
                secondary["footystats"] = {
                    "home": self.footystats.team_state(league_code, home_name),
                    "away": self.footystats.team_state(league_code, away_name),
                    "model_usage": "reconciliation_only",
                }
            except Exception as exc:
                secondary["footystats"] = {
                    "available": False,
                    "error": safe_error(exc),
                    "model_usage": "reconciliation_only",
                }

        if self.sportmonks.connected:
            secondary["sportmonks"] = {
                "connected": True,
                "model_usage": "coverage_audit_only",
                "note": (
                    "Sportmonks fixture IDs are provider-specific. No data is merged "
                    "until competition + kickoff + both teams pass a strict reconciliation gate."
                ),
            }

        current["secondary_reconciliation"] = secondary
        return analysis
