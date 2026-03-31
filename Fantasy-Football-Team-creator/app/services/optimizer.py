from __future__ import annotations

from itertools import combinations

from app.services.ranking import RankedPlayer


def is_valid_outfield_selection(players: list[RankedPlayer]) -> bool:
    defenders = sum(1 for player in players if player.position == "DEF")
    midfielders = sum(1 for player in players if player.position == "MID")
    forwards = sum(1 for player in players if player.position == "FWD")
    return (
        3 <= defenders <= 5
        and 2 <= midfielders <= 5
        and 1 <= forwards <= 3
        and len(players) == 10
    )


def optimize_lineup(ranked_players: list[RankedPlayer]) -> dict:
    goalkeepers = [player for player in ranked_players if player.position == "GKP"]
    outfield = [player for player in ranked_players if player.position != "GKP"]

    starter_goalkeeper = max(goalkeepers, key=lambda player: player.overall_score, default=None)
    reserve_goalkeeper = None
    if starter_goalkeeper:
        reserve_candidates = [player for player in goalkeepers if player.player_name != starter_goalkeeper.player_name]
        reserve_goalkeeper = max(
            reserve_candidates,
            key=lambda player: player.overall_score,
            default=None,
        )

    best_outfield = []
    best_score = -1.0
    for combo in combinations(outfield, 10):
        if not is_valid_outfield_selection(list(combo)):
            continue
        score = sum(player.overall_score for player in combo)
        if score > best_score:
            best_score = score
            best_outfield = list(combo)

    starters = []
    if starter_goalkeeper:
        starters.append(starter_goalkeeper)
    starters.extend(sorted(best_outfield, key=lambda player: player.overall_score, reverse=True))

    bench = [
        player
        for player in ranked_players
        if player.player_name not in {starter.player_name for starter in starters}
        and (not reserve_goalkeeper or player.player_name != reserve_goalkeeper.player_name)
    ]
    bench.sort(key=lambda player: player.overall_score, reverse=True)

    formation_counts = {
        "DEF": sum(1 for player in starters if player.position == "DEF"),
        "MID": sum(1 for player in starters if player.position == "MID"),
        "FWD": sum(1 for player in starters if player.position == "FWD"),
    }

    return {
        "starters": starters,
        "bench": bench,
        "reserve_goalkeeper": reserve_goalkeeper,
        "formation": f"1-{formation_counts['DEF']}-{formation_counts['MID']}-{formation_counts['FWD']}",
    }


def validate_manual_selection(starters: list[RankedPlayer]) -> str | None:
    if len(starters) != 11:
        return "Please choose exactly 11 starters."

    goalkeepers = [player for player in starters if player.position == "GKP"]
    if len(goalkeepers) != 1:
        return "A valid lineup must include exactly one goalkeeper."

    outfield = [player for player in starters if player.position != "GKP"]
    if not is_valid_outfield_selection(outfield):
        return "That lineup is not a valid FPL formation. Use at least 3 DEF, 2 MID, and 1 FWD."

    return None
