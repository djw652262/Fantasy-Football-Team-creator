from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_saved_lineups, get_squad_entries, init_db, save_lineup, save_squad_entries
from app.fpl_client import CacheMissError, FPLClient
from app.services.optimizer import optimize_lineup, validate_manual_selection
from app.services.ranking import RankedPlayer, normalize_name, rank_squad


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Fantasy Football Team Creator")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
client = FPLClient()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def build_base_context(request: Request, flash_message: str | None = None, selection_error: str | None = None) -> dict:
    cache_status = client.get_cache_status()
    return {
        "request": request,
        "flash_message": flash_message,
        "selection_error": selection_error,
        "cache_status": cache_status,
    }


def build_recommendation_context(request: Request, flash_message: str | None = None, selection_error: str | None = None) -> dict:
    context = build_base_context(request, flash_message, selection_error)
    squad_entries = get_squad_entries()

    try:
        ranking_data = rank_squad([dict(entry) for entry in squad_entries], client, use_cache_only=True)
        optimized = optimize_lineup(ranking_data["ranked_players"])
        context.update(
            {
                "data_ready": True,
                "squad_entries": squad_entries,
                "current_gameweek": ranking_data["current_gameweek"],
                "ranked_players": ranking_data["ranked_players"],
                "unresolved_names": ranking_data["unresolved_names"],
                "recommended_starters": optimized["starters"],
                "recommended_bench": optimized["bench"],
                "reserve_goalkeeper": optimized["reserve_goalkeeper"],
                "recommended_formation": optimized["formation"],
            }
        )
    except CacheMissError:
        context.update(
            {
                "data_ready": False,
                "squad_entries": squad_entries,
                "current_gameweek": None,
                "ranked_players": [],
                "unresolved_names": [],
                "recommended_starters": [],
                "recommended_bench": [],
                "reserve_goalkeeper": None,
                "recommended_formation": None,
            }
        )

    return context


def build_player_options_from_cache() -> list[dict]:
    try:
        bootstrap = client.get_bootstrap(use_cache_only=True)
    except CacheMissError:
        return []

    teams = {team["id"]: team for team in bootstrap["teams"]}
    position_labels = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
    return [
        {
            "id": player["id"],
            "label": f"{player['web_name']} - {teams[player['team']]['short_name']} - {position_labels[player['element_type']]}",
            "name": player["web_name"],
            "team": teams[player["team"]]["short_name"],
            "position": position_labels[player["element_type"]],
        }
        for player in sorted(
            bootstrap["elements"],
            key=lambda item: (item["element_type"], teams[item["team"]]["short_name"], item["web_name"]),
        )
    ]


def resolve_squad_element_ids(squad_entries: list, bootstrap: dict) -> list[int]:
    elements = bootstrap["elements"]
    id_lookup = {int(player["id"]): int(player["id"]) for player in elements}
    name_lookup: dict[str, int] = {}
    for player in elements:
        names = {
            player["web_name"],
            player["first_name"],
            player["second_name"],
            f"{player['first_name']} {player['second_name']}",
        }
        for name in names:
            name_lookup.setdefault(normalize_name(name), int(player["id"]))

    resolved_ids: list[int] = []
    for entry in squad_entries:
        player_id = entry["player_id"]
        player_name = str(entry["player_name"]).strip()
        if player_id is not None and int(player_id) in id_lookup:
            resolved_ids.append(int(player_id))
            continue
        if player_name:
            matched_id = name_lookup.get(normalize_name(player_name))
            if matched_id:
                resolved_ids.append(matched_id)
    return resolved_ids


@app.get("/", response_class=HTMLResponse)
def home(request: Request, refreshed: int = 0) -> HTMLResponse:
    flash = "FPL data refreshed." if refreshed else None
    context = build_recommendation_context(request, flash_message=flash)
    return templates.TemplateResponse("recommendations.html", context)


@app.post("/refresh-data")
def refresh_data() -> RedirectResponse:
    bootstrap = client.refresh_core_data()
    squad_entries = get_squad_entries()
    element_ids = resolve_squad_element_ids(squad_entries, bootstrap)
    if element_ids:
        client.refresh_player_summaries(element_ids)
    return RedirectResponse(url="/?refreshed=1", status_code=303)


@app.get("/squad", response_class=HTMLResponse)
def squad_editor(request: Request, saved: int = 0) -> HTMLResponse:
    flash = "Squad saved." if saved else None
    context = build_base_context(request, flash_message=flash)
    context.update(
        {
            "squad_entries": get_squad_entries(),
            "player_options": build_player_options_from_cache(),
        }
    )
    return templates.TemplateResponse("squad.html", context)


@app.post("/squad")
def update_squad(
    slot_1: str = Form(""),
    slot_1_name: str = Form(""),
    slot_2: str = Form(""),
    slot_2_name: str = Form(""),
    slot_3: str = Form(""),
    slot_3_name: str = Form(""),
    slot_4: str = Form(""),
    slot_4_name: str = Form(""),
    slot_5: str = Form(""),
    slot_5_name: str = Form(""),
    slot_6: str = Form(""),
    slot_6_name: str = Form(""),
    slot_7: str = Form(""),
    slot_7_name: str = Form(""),
    slot_8: str = Form(""),
    slot_8_name: str = Form(""),
    slot_9: str = Form(""),
    slot_9_name: str = Form(""),
    slot_10: str = Form(""),
    slot_10_name: str = Form(""),
    slot_11: str = Form(""),
    slot_11_name: str = Form(""),
    slot_12: str = Form(""),
    slot_12_name: str = Form(""),
    slot_13: str = Form(""),
    slot_13_name: str = Form(""),
    slot_14: str = Form(""),
    slot_14_name: str = Form(""),
    slot_15: str = Form(""),
    slot_15_name: str = Form(""),
) -> RedirectResponse:
    raw_entries = [
        (slot_1, slot_1_name),
        (slot_2, slot_2_name),
        (slot_3, slot_3_name),
        (slot_4, slot_4_name),
        (slot_5, slot_5_name),
        (slot_6, slot_6_name),
        (slot_7, slot_7_name),
        (slot_8, slot_8_name),
        (slot_9, slot_9_name),
        (slot_10, slot_10_name),
        (slot_11, slot_11_name),
        (slot_12, slot_12_name),
        (slot_13, slot_13_name),
        (slot_14, slot_14_name),
        (slot_15, slot_15_name),
    ]
    save_squad_entries(
        [
            {
                "player_id": int(player_id) if str(player_id).strip() else None,
                "player_name": player_name.strip(),
            }
            for player_id, player_name in raw_entries
        ]
    )
    return RedirectResponse(url="/squad?saved=1", status_code=303)


@app.get("/recommendations", response_class=HTMLResponse)
def recommendations(request: Request, saved: int = 0) -> HTMLResponse:
    flash = "Lineup saved." if saved else None
    context = build_recommendation_context(request, flash_message=flash)
    return templates.TemplateResponse("recommendations.html", context)


@app.post("/save-lineup", response_class=HTMLResponse)
def save_lineup_route(
    request: Request,
    gameweek: int = Form(...),
    starters: list[str] = Form(default=[]),
):
    context = build_recommendation_context(request)
    if not context["data_ready"]:
        context["selection_error"] = "Refresh FPL data before saving a lineup."
        return templates.TemplateResponse("recommendations.html", context, status_code=400)

    ranked_by_name = {player.player_name: player for player in context["ranked_players"]}
    selected_players: list[RankedPlayer] = [
        ranked_by_name[name] for name in starters if name in ranked_by_name
    ]

    error_message = validate_manual_selection(selected_players)
    if error_message:
        context.update(
            {
                "selection_error": error_message,
                "manual_starters": starters,
            }
        )
        return templates.TemplateResponse("recommendations.html", context, status_code=400)

    remaining_players = [
        player
        for player in context["ranked_players"]
        if player.player_name not in {starter.player_name for starter in selected_players}
    ]
    reserve_goalkeeper = next(
        (player for player in remaining_players if player.position == "GKP"),
        None,
    )
    bench = [player for player in remaining_players if player.position != "GKP"]
    bench.sort(key=lambda player: player.overall_score, reverse=True)

    save_lineup(
        gameweek=gameweek,
        starters=[player.player_name for player in selected_players],
        bench=[player.player_name for player in bench],
        reserve_goalkeeper=reserve_goalkeeper.player_name if reserve_goalkeeper else None,
    )
    return RedirectResponse(url="/recommendations?saved=1", status_code=303)


@app.get("/history", response_class=HTMLResponse)
def history(request: Request) -> HTMLResponse:
    context = build_base_context(request)
    saved_lineups = get_saved_lineups()

    try:
        bootstrap = client.get_bootstrap(use_cache_only=True)
        players = {player["web_name"]: player for player in bootstrap["elements"]}
    except CacheMissError:
        players = {}

    for lineup in saved_lineups:
        lineup["total_points"] = None
        if not players:
            continue

        try:
            event_live = client.get_event_live(lineup["gameweek"], use_cache_only=True)
            live_points = {
                item["id"]: item["stats"]["total_points"] for item in event_live.get("elements", [])
            }
            total_points = 0
            for player in lineup["players"]:
                if player["role"] != "starter":
                    continue
                player_row = players.get(player["player_name"])
                if player_row:
                    total_points += live_points.get(player_row["id"], 0)
            lineup["total_points"] = total_points
        except CacheMissError:
            lineup["total_points"] = None

    context["saved_lineups"] = saved_lineups
    return templates.TemplateResponse("history.html", context)
