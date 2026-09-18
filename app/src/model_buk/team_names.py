from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


# Cross-provider name variants. A provider can use different canonical names for
# the same club, so each input alias may resolve to more than one candidate form.
ALIAS_VARIANTS: dict[str, tuple[str, ...]] = {
    # England
    "manchester city": ("Man City", "Manchester City"),
    "man city": ("Man City", "Manchester City"),
    "manchester united": ("Man United", "Manchester United"),
    "man united": ("Man United", "Manchester United"),
    "nottingham forest": ("Nottm Forest", "Nottingham Forest"),
    "nott'm forest": ("Nottm Forest", "Nottingham Forest"),
    "afc bournemouth": ("Bournemouth", "AFC Bournemouth"),
    "brighton & hove albion": ("Brighton", "Brighton & Hove Albion"),
    "wolverhampton wanderers": ("Wolves", "Wolverhampton Wanderers"),
    # Spain
    "atletico madrid": ("Ath Madrid", "Atletico Madrid"),
    "atl. madrid": ("Ath Madrid", "Atletico Madrid"),
    "athletic club": ("Ath Bilbao", "Athletic Club", "Athletic Bilbao"),
    "athletic bilbao": ("Ath Bilbao", "Athletic Club", "Athletic Bilbao"),
    "ath bilbao": ("Ath Bilbao", "Athletic Club", "Athletic Bilbao"),
    "real betis": ("Betis", "Real Betis"),
    "real sociedad": ("Sociedad", "Real Sociedad"),
    "rayo vallecano": ("Vallecano", "Rayo Vallecano"),
    # Germany
    "bayern munich": ("Bayern Munich", "Bayern München"),
    "borussia dortmund": ("Dortmund", "Borussia Dortmund"),
    "borussia monchengladbach": ("MGladbach", "Borussia M'gladbach", "Borussia Monchengladbach"),
    "borussia m'gladbach": ("MGladbach", "Borussia M'gladbach", "Borussia Monchengladbach"),
    "eintracht frankfurt": ("Ein Frankfurt", "Eintracht Frankfurt"),
    "bayer leverkusen": ("Leverkusen", "Bayer Leverkusen"),
    "1. fc koln": ("FC Koln", "FC Köln", "1. FC Koln"),
    "rb leipzig": ("RB Leipzig",),
    # Italy
    "ac milan": ("Milan", "AC Milan"),
    "as roma": ("Roma", "AS Roma"),
    "inter milan": ("Inter", "Inter Milan", "Internazionale"),
    "internazionale": ("Inter", "Inter Milan", "Internazionale"),
    # France
    "paris saint germain": ("Paris SG", "Paris Saint Germain", "Paris Saint-Germain"),
    "paris saint-germain": ("Paris SG", "Paris Saint Germain", "Paris Saint-Germain"),
    "psg": ("Paris SG", "Paris Saint Germain", "Paris Saint-Germain"),
    # Poland
    "lech poznan": ("Lech Poznan", "Lech Poznań"),
    "legia warszawa": ("Legia", "Legia Warszawa"),
    "jagiellonia bialystok": ("Jagiellonia", "Jagiellonia Bialystok", "Jagiellonia Białystok"),
    "pogon szczecin": ("Pogon Szczecin", "Pogoń Szczecin"),
    "gornik zabrze": ("Gornik Zabrze", "Górnik Zabrze"),
    "rakow czestochowa": ("Rakow", "Rakow Czestochowa", "Raków Częstochowa"),
    "lechia gdansk": ("Lechia Gdansk", "Lechia Gdańsk"),
    "gks katowice": ("GKS Katowice",),
    "widzew lodz": ("Widzew Lodz", "Widzew Łódź"),
    "korona kielce": ("Korona Kielce",),
    "piast gliwice": ("Piast Gliwice",),
    "radomiak radom": ("Radomiak Radom",),
    "motor lublin": ("Motor Lublin",),
    "wisla plock": ("Wisla Plock", "Wisła Płock"),
}


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"\b(fc|afc|cf|sc|ssc|ac|as|sv|vfb|1\.)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def resolve_team_name(name: str, candidates: list[str]) -> tuple[str | None, float]:
    """Resolve one provider name against another provider's candidate set.

    Exact matches win first. Then known cross-provider variants are tried. Only
    after that do we use fuzzy matching. This avoids cases like API-Football's
    "Athletic Bilbao" being forced to football-data's "Ath Bilbao" when the
    target provider actually calls the same club "Athletic Club".
    """
    raw = str(name).strip()
    if raw in candidates:
        return raw, 1.0

    target = normalize_name(raw)
    if not target:
        return None, 0.0

    # Alias keys must undergo the same punctuation/accent normalization as input.
    variants = next((forms for alias, forms in ALIAS_VARIANTS.items()
                     if normalize_name(alias) == target), ())
    for variant in variants:
        if variant in candidates:
            return variant, 1.0

    candidate_norm: dict[str, list[str]] = {}
    for candidate in candidates:
        candidate_norm.setdefault(normalize_name(candidate), []).append(candidate)
    if target in candidate_norm and len(candidate_norm[target]) == 1:
        return candidate_norm[target][0], 1.0
    for variant in variants:
        norm = normalize_name(variant)
        if norm in candidate_norm and len(candidate_norm[norm]) == 1:
            return candidate_norm[norm][0], 1.0

    # Compare both the raw normalized input and all known variants. We retain a
    # conservative threshold; uncertain entity matches must fail rather than feed
    # the wrong club into a predictive model.
    query_forms = [target] + [normalize_name(v) for v in variants]
    best_name: str | None = None
    best_score = 0.0
    for candidate in candidates:
        cand = normalize_name(candidate)
        score = max(SequenceMatcher(None, q, cand).ratio() for q in query_forms)
        if score > best_score:
            best_name, best_score = candidate, score
    # A high string similarity is not proof of club identity (e.g. Manchester
    # United/City). Keep the score for diagnostics, but require an explicit alias.
    return None, best_score
