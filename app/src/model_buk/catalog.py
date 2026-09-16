from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeagueSpec:
    code: str
    name: str
    country: str
    historical_division: str | None
    api_football_id: int
    default_season_start_month: int = 7
    group: str = "domestic"
    analysis_tier: str = "B"


# Historical coverage retained internally. The UI exposes PRIMARY_CODES only.
LEAGUES: dict[str, LeagueSpec] = {
    "EPL": LeagueSpec("EPL", "Premier League", "England", "E0", 39, analysis_tier="A"),
    "CHAMPIONSHIP": LeagueSpec("CHAMPIONSHIP", "Championship", "England", "E1", 40, analysis_tier="C"),
    "LALIGA": LeagueSpec("LALIGA", "LaLiga", "Spain", "SP1", 140, analysis_tier="A"),
    "LALIGA2": LeagueSpec("LALIGA2", "LaLiga 2", "Spain", "SP2", 141, analysis_tier="C"),
    "BUNDESLIGA": LeagueSpec("BUNDESLIGA", "Bundesliga", "Germany", "D1", 78, analysis_tier="A"),
    "BUNDESLIGA2": LeagueSpec("BUNDESLIGA2", "2. Bundesliga", "Germany", "D2", 79, analysis_tier="C"),
    "SERIEA": LeagueSpec("SERIEA", "Serie A", "Italy", "I1", 135, analysis_tier="A"),
    "SERIEB": LeagueSpec("SERIEB", "Serie B", "Italy", "I2", 136, analysis_tier="C"),
    "LIGUE1": LeagueSpec("LIGUE1", "Ligue 1", "France", "F1", 61, analysis_tier="A"),
    "LIGUE2": LeagueSpec("LIGUE2", "Ligue 2", "France", "F2", 62, analysis_tier="C"),
    "PRIMEIRA": LeagueSpec("PRIMEIRA", "Primeira Liga", "Portugal", "P1", 94, analysis_tier="B"),
    "EREDIVISIE": LeagueSpec("EREDIVISIE", "Eredivisie", "Netherlands", "N1", 88, analysis_tier="B"),
    "BELGIUM": LeagueSpec("BELGIUM", "Belgian Pro League", "Belgium", "B1", 144, analysis_tier="B"),
    "SUPERLIG": LeagueSpec("SUPERLIG", "Süper Lig", "Turkey", "T1", 203, analysis_tier="B"),
    "SCOTLAND": LeagueSpec("SCOTLAND", "Scottish Premiership", "Scotland", "SC0", 179, analysis_tier="C"),
    "EKSTRAKLASA": LeagueSpec("EKSTRAKLASA", "Ekstraklasa", "Poland", "POL", 106, analysis_tier="B"),
    # UEFA competitions are live-visible now. Competition-specific historical state is not yet in the local feature store.
    "UCL": LeagueSpec("UCL", "UEFA Champions League", "Europe", None, 2, group="europe", analysis_tier="LIVE"),
    "UEL": LeagueSpec("UEL", "UEFA Europa League", "Europe", None, 3, group="europe", analysis_tier="LIVE"),
    "UECL": LeagueSpec("UECL", "UEFA Conference League", "Europe", None, 848, group="europe", analysis_tier="LIVE"),
}

PRIMARY_CODES = [
    "EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1",
    "EREDIVISIE", "PRIMEIRA", "BELGIUM", "SUPERLIG", "EKSTRAKLASA",
    "UCL", "UEL", "UECL",
]

DIVISION_TO_LEAGUE = {v.historical_division: v for v in LEAGUES.values() if v.historical_division}
API_ID_TO_LEAGUE = {v.api_football_id: v for v in LEAGUES.values()}


def league_catalog(primary_only: bool = True) -> list[dict]:
    codes = PRIMARY_CODES if primary_only else list(LEAGUES)
    return [
        {
            "code": LEAGUES[code].code,
            "name": LEAGUES[code].name,
            "country": LEAGUES[code].country,
            "historical_division": LEAGUES[code].historical_division,
            "api_football_id": LEAGUES[code].api_football_id,
            "group": LEAGUES[code].group,
            "analysis_tier": LEAGUES[code].analysis_tier,
        }
        for code in codes
    ]


def season_for_date(year: int, month: int, start_month: int = 7) -> int:
    return year if month >= start_month else year - 1
