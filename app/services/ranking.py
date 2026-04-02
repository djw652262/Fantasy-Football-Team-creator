from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.fpl_client import FPLClient


POSITION_MAP = {
    1: "GKP",
    2: "DEF",
    3: "MID",
    4: "FWD",
}

STATUS_SCORE = {
    "a": 10.0,
    "d": 4.0,
    "i": 0.0,
    "s": 1.5,
    "u": 5.0,
}


@dataclass
class RankedPlayer:
    player_name: str
    matched_name: str
    team_name: str
    position: str
    opponent: str
    venue: str
    difficulty: int
    status: str
    chance_of_playing: int | None
    recent_points: float
    recent_minutes: float
    starts_estimate: int
    overall_score: float
    form_score: float
    fitness_score: float
    minutes_score: float
    fixture_score: float
    value_score: float
    explanation: str
    element_id: int


def normalize_name(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def get_next_gameweek(bootstrap: dict) -> int:
    next_event = next((event for event in bootstrap["events"] if event["is_next"]), None)
    if next_event:
        return int(next_event["id"])

    current_event = next((event for event in bootstrap["events"] if event["is_current"]), None)
    if current_event:
        return int(current_event["id"])

    return int(bootstrap["events"][0]["id"])


def build_name_lookup(elements: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for element in elements:
        options = {
            element["web_name"],
            element["first_name"],
            element["second_name"],
            f"{element['first_name']} {element['second_name']}",
        }
        for option in options:
            lookup.setdefault(normalize_name(option), element)
    return lookup


def build_id_lookup(elements: list[dict]) -> dict[int, dict]:
    return {int(element["id"]): element for element in elements}


def get_next_fixture(team_id: int, next_gameweek: int, fixtures: list[dict], teams: dict[int, dict]) -> tuple[str, str, int]:
    relevant = [
        fixture
        for fixture in fixtures
        if fixture.get("event") == next_gameweek and (fixture["team_h"] == team_id or fixture["team_a"] == team_id)
    ]
    if not relevant:
        return ("Unknown", "TBD", 3)

    fixture = relevant[0]
    is_home = fixture["team_h"] == team_id
    opponent_id = fixture["team_a"] if is_home else fixture["team_h"]
    difficulty = fixture["team_h_difficulty"] if is_home else fixture["team_a_difficulty"]
    opponent_name = teams[opponent_id]["short_name"]
    return (opponent_name, "H" if is_home else "A", int(difficulty))


def score_player(element: dict, summary: dict, opponent: str, venue: str, difficulty: int, teams: dict[int, dict]) -> RankedPlayer:
    history = summary.get("history", [])[-3:]
    recent_points = mean([match["total_points"] for match in history]) if history else float(element["form"] or 0)
    recent_minutes = mean([match["minutes"] for match in history]) if history else 0.0
    starts_estimate = sum(1 for match in history if match["minutes"] >= 60)

    chance_raw = element.get("chance_of_playing_next_round")
    chance_of_playing = int(chance_raw) if chance_raw is not None else None

    form_score = clamp(recent_points * 1.7, 0.0, 10.0)
    minutes_score = clamp((recent_minutes / 90.0) * 10.0, 0.0, 10.0)
    fitness_score = clamp(
        (chance_of_playing / 10.0) if chance_of_playing is not None else STATUS_SCORE.get(element["status"], 5.0),
        0.0,
        10.0,
    )
    fixture_score = clamp((6 - difficulty) * 2.0, 0.0, 10.0)
    value_score = clamp(float(element.get("points_per_game") or 0) * 1.2, 0.0, 10.0)

    overall_score = round(
        (form_score * 0.35)
        + (minutes_score * 0.25)
        + (fitness_score * 0.20)
        + (fixture_score * 0.15)
        + (value_score * 0.05),
        2,
    )

    fitness_blurb = (
        f"{chance_of_playing}% chance of playing"
        if chance_of_playing is not None
        else f"status flag: {element['status']}"
    )
    explanation = (
        f"{teams[element['team']]['short_name']} vs {opponent} ({venue}), "
        f"recent points {recent_points:.1f}, recent minutes {recent_minutes:.0f}, "
        f"{fitness_blurb}."
    )

    return RankedPlayer(
        player_name=element["web_name"],
        matched_name=f"{element['first_name']} {element['second_name']}",
        team_name=teams[element["team"]]["name"],
        position=POSITION_MAP[element["element_type"]],
        opponent=opponent,
        venue=venue,
        difficulty=difficulty,
        status=element["status"],
        chance_of_playing=chance_of_playing,
        recent_points=round(recent_points, 2),
        recent_minutes=round(recent_minutes, 1),
        starts_estimate=starts_estimate,
        overall_score=overall_score,
        form_score=round(form_score, 2),
        fitness_score=round(fitness_score, 2),
        minutes_score=round(minutes_score, 2),
        fixture_score=round(fixture_score, 2),
        value_score=round(value_score, 2),
        explanation=explanation,
        element_id=element["id"],
    )


def rank_squad(squad_entries: list[dict], client: FPLClient, use_cache_only: bool = False) -> dict:
    bootstrap = client.get_bootstrap(use_cache_only=use_cache_only)
    fixtures = client.get_fixtures(use_cache_only=use_cache_only)
    next_gameweek = get_next_gameweek(bootstrap)

    teams = {team["id"]: team for team in bootstrap["teams"]}
    elements = bootstrap["elements"]
    lookup = build_name_lookup(elements)
    id_lookup = build_id_lookup(elements)

    ranked: list[RankedPlayer] = []
    unresolved: list[str] = []

    for entry in squad_entries:
        clean_name = str(entry.get("player_name", "")).strip()
        player_id = entry.get("player_id")
        element = None

        if player_id is not None:
            try:
                element = id_lookup.get(int(player_id))
            except (TypeError, ValueError):
                element = None

        if not clean_name:
            clean_name = ""

        if not element and clean_name:
            element = lookup.get(normalize_name(clean_name))

        if not element:
            if clean_name:
                unresolved.append(clean_name)
            continue

        summary = client.get_element_summary(int(element["id"]), use_cache_only=use_cache_only)
        opponent, venue, difficulty = get_next_fixture(
            int(element["team"]), next_gameweek, fixtures, teams
        )
        ranked.append(score_player(element, summary, opponent, venue, difficulty, teams))

    ranked.sort(key=lambda player: player.overall_score, reverse=True)
    return {
        "current_gameweek": next_gameweek,
        "ranked_players": ranked,
        "unresolved_names": unresolved,
    }
