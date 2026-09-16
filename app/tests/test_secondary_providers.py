from model_buk.secondary_providers import FootyStatsClient, SportmonksClient


def test_secondary_clients_are_optional_without_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("FOOTYSTATS_API_KEY", raising=False)
    monkeypatch.delenv("SPORTMONKS_API_TOKEN", raising=False)
    footy = FootyStatsClient(cache_dir=tmp_path / "footy")
    sport = SportmonksClient(cache_dir=tmp_path / "sport")
    assert footy.connected is False
    assert sport.connected is False
    assert footy.status()["probability_input"] is False
    assert sport.status()["probability_input"] is False


def test_secondary_keys_are_never_exposed_in_status(tmp_path):
    footy = FootyStatsClient(api_key="secret-footy", cache_dir=tmp_path / "footy")
    sport = SportmonksClient(api_token="secret-sport", cache_dir=tmp_path / "sport")
    assert footy.status()["connected"] is True
    assert sport.status()["connected"] is True
    assert "secret" not in str(footy.status()).lower()
    assert "secret" not in str(sport.status()).lower()
