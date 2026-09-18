from datetime import datetime, timedelta, timezone

import pytest
import requests

from model_buk.live_provider import ApiFootballClient
from model_buk.secondary_providers import FootyStatsClient, SportmonksClient
from model_buk.security import safe_error
from model_buk.team_names import resolve_team_name
from model_buk.weather import forecast_for_kickoff, geocode_city


def test_identity_requires_alias_not_fuzzy_similarity():
    assert resolve_team_name("Manchester United", ["Manchester City"])[0] is None
    assert resolve_team_name("Brighton & Hove Albion", ["Brighton"])[0] == "Brighton"
    assert resolve_team_name("Athletic Bilbao", ["Athletic Club"])[0] == "Athletic Club"
    assert resolve_team_name("", ["Arsenal"])[0] is None


def test_explicit_empty_key_disables_environment_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv('API_FOOTBALL_KEY', 'synthetic-env-key')
    assert not ApiFootballClient(api_key='', cache_dir=tmp_path).connected


def test_plan_rejection_exposes_reason_without_secret(tmp_path, monkeypatch):
    from model_buk.security import ProviderAccessError
    client = ApiFootballClient(api_key='SYNTHETIC_PRIVATE_KEY', cache_dir=tmp_path)
    class Response:
        headers = {}
        def raise_for_status(self): pass
        def json(self): return {'errors': {'plan': 'Free plans do not have access: SYNTHETIC_PRIVATE_KEY'}}
    monkeypatch.setattr(client._session, 'get', lambda *a, **kw: Response())
    with pytest.raises(ProviderAccessError) as caught:
        client._get('/fixtures', {'team': 1, 'last': 20})
    assert 'Plan API' in str(caught.value)
    assert 'SYNTHETIC_PRIVATE_KEY' not in str(caught.value)
    assert client.status()['access_error']


@pytest.mark.parametrize("provider", ["footy", "sport", "api"])
def test_transport_errors_do_not_expose_query_credentials(tmp_path, monkeypatch, provider):
    secret = "test-secret-do-not-return"
    if provider == "footy":
        client = FootyStatsClient(api_key=secret, cache_dir=tmp_path)
    elif provider == "sport":
        client = SportmonksClient(api_token=secret, cache_dir=tmp_path)
    else:
        client = ApiFootballClient(api_key=secret, cache_dir=tmp_path)
    response = requests.Response()
    response.status_code = 401
    response.url = "https://example.test/?key=" + secret
    monkeypatch.setattr(client._session, "get", lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError) as error:
        client._get("/test")
    assert secret not in str(error.value)
    assert "401" in str(error.value)
    assert secret not in safe_error(ValueError(secret))


def test_footystats_rejects_wrong_country_empty_name_and_wrong_season(tmp_path, monkeypatch):
    client = FootyStatsClient(api_key="test", cache_dir=tmp_path)
    when = datetime(2026, 2, 1, tzinfo=timezone.utc)
    rows = [{"name": "Premier League", "country": "South Africa", "season": [{"id": 1, "year": 2025}]}]
    monkeypatch.setattr(client, "league_list", lambda **kw: rows)
    assert client.resolve_season_id("EPL", when) is None
    rows[0]["country"] = "England"
    rows[0]["season"].append({"id": 2, "year": 2026})
    assert client.resolve_season_id("EPL", when) == 1
    monkeypatch.setattr(client, "resolve_season_id", lambda *a: 1)
    monkeypatch.setattr(client, "league_teams", lambda *a, **kw: [{"id": 9, "name": "", "stats": {"pointsPerGame": 3}}])
    assert client.team_state("EPL", "Arsenal") is None


def test_statistics_preserve_null_zero_and_invalid_values(tmp_path, monkeypatch):
    client = ApiFootballClient(api_key="test", cache_dir=tmp_path)
    monkeypatch.setattr(client, "_get", lambda *a, **kw: {"response": [{"team": {"id": 1}, "statistics": [
        {"type": "Corner Kicks", "value": None}, {"type": "Shots on Goal", "value": 0},
        {"type": "Yellow Cards", "value": None}, {"type": "Total Shots", "value": "nan"},
    ]}]})
    result = client.fixture_statistics(1)[1]
    assert result == {"corners": None, "sot": 0, "yellow": None, "shots": None}


def _fixture(fid, when, status="FT", league=39):
    return {"fixture_id": fid, "kickoff": when.isoformat(), "status": status, "league_id": league,
            "home": {"id": 1, "name": "A", "goals": 2}, "away": {"id": 2, "name": "B", "goals": 1}}


def test_observations_cutoff_identity_null_cards_and_cross_competition(tmp_path, monkeypatch):
    client = ApiFootballClient(api_key="test", cache_dir=tmp_path)
    boundary = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fixtures = [
        _fixture(1, boundary - timedelta(days=4), league=39),
        _fixture(2, boundary - timedelta(days=8), league=2),
        _fixture(3, boundary + timedelta(days=1)),
        _fixture(4, boundary - timedelta(hours=1)),
        _fixture(5, boundary - timedelta(days=2), status="AET"),
        _fixture(6, boundary - timedelta(days=3), status="2H"),
    ]
    fixture_args = {}
    monkeypatch.setattr(client, "recent_fixtures", lambda *a, **kw: fixture_args.update(kw) or fixtures)
    monkeypatch.setattr(client, "fixture_statistics", lambda fid: {1: {"yellow": 2, "red": None}, 2: {"yellow": 0, "red": 0}})
    result = client.current_observations(1, cutoff=boundary)
    assert {row["fixture_id"] for row in result} == {1, 2}
    assert fixture_args["league_id"] is None and fixture_args["season"] is None
    assert result[0]["opponent_id"] == 2 and result[0]["team_id"] == 1
    assert result[0]["cards_for"] is None and result[0]["cards_against"] == 0
    assert result[0]["availability"]["cards_for"] is False
    assert datetime.fromisoformat(result[0]["available_at"]) < boundary


def test_failed_statistics_requests_count_against_budget(tmp_path, monkeypatch):
    client = ApiFootballClient(api_key="test", cache_dir=tmp_path)
    boundary = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(client, "recent_fixtures", lambda *a, **kw: [_fixture(i, boundary - timedelta(days=i + 2)) for i in range(8)])
    attempts = []
    def fail(fid):
        attempts.append(fid)
        raise RuntimeError("quota")
    monkeypatch.setattr(client, "fixture_statistics", fail)
    result = client.current_observations(1, cutoff=boundary, max_stat_calls=2)
    assert len(attempts) == 2 and len(result) == 8


def test_odds_pagination_is_read_with_explicit_cost_cap(tmp_path, monkeypatch):
    client = ApiFootballClient(api_key='test', cache_dir=tmp_path)
    calls=[]
    def page(endpoint, params, ttl):
        number=params.get('page',1);calls.append(number)
        return {'paging':{'total':3},'response':[{'update':'2026-09-17T12:00:00Z','bookmakers':[{'id':number,'name':str(number),'bets':[{'id':5,'name':'Goals Over/Under','values':[{'value':'Over 2.5','odd':'2.0'}]}]}]}]}
    monkeypatch.setattr(client,'_get',page)
    monkeypatch.setenv('MODEL_BUK_MAX_ODDS_PAGES','2')
    rows=client.odds(1)
    assert calls == [1,2]
    assert len(rows)==2 and all(r['feed_complete'] is False for r in rows)


@pytest.mark.parametrize("status,days", [("FT", -1), ("1H", 1), ("PST", 1)])
def test_prematch_rejects_played_inplay_or_postponed_fixture(tmp_path, monkeypatch, status, days):
    client = ApiFootballClient(api_key="test", cache_dir=tmp_path)
    monkeypatch.setattr(client, "fixture", lambda fid: _fixture(fid, datetime.now(timezone.utc) + timedelta(days=days), status))
    with pytest.raises(ValueError, match="Prematch"):
        client.match_context(1)


class _Response:
    def __init__(self, data): self.data = data
    def raise_for_status(self): pass
    def json(self): return self.data


def test_weather_rejects_outside_forecast_horizon(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _Response({"hourly": {
        "time": ["2026-09-16T12:00", "2026-09-16T13:00"], "temperature_2m": [35, 36]}}))
    assert forecast_for_kickoff(50, 20, "2026-12-20T12:00Z") is None
    assert forecast_for_kickoff(50, 20, "2026-09-16T12:30Z")["temperature_c"] == 35


def test_geocoding_does_not_accept_wrong_country(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _Response({"results": [
        {"name": "London", "country": "Canada", "latitude": 43, "longitude": -81}]}))
    assert geocode_city("London", "England") is None
