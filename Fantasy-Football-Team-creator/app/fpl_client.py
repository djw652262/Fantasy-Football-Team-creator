from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen


BASE_URL = "https://fantasy.premierleague.com/api"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "fpl_cache"


class CacheMissError(RuntimeError):
    pass


class FPLClient:
    def __init__(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_json(self, path: str) -> dict | list:
        with urlopen(f"{BASE_URL}{path}") as response:
            return json.load(response)

    def _cache_path(self, cache_key: str) -> Path:
        return CACHE_DIR / f"{cache_key}.json"

    def _write_cache(self, cache_key: str, data: dict | list) -> None:
        payload = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self._cache_path(cache_key).write_text(json.dumps(payload), encoding="utf-8")

    def _read_cache_payload(self, cache_key: str) -> dict:
        path = self._cache_path(cache_key)
        if not path.exists():
            raise CacheMissError(f"No cached data found for {cache_key}.")
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_cache_data(self, cache_key: str) -> dict | list:
        return self._read_cache_payload(cache_key)["data"]

    def _is_fresh(self, cache_key: str, max_age_minutes: int) -> bool:
        try:
            payload = self._read_cache_payload(cache_key)
        except CacheMissError:
            return False

        cached_at = datetime.fromisoformat(payload["cached_at"])
        return datetime.now(timezone.utc) - cached_at <= timedelta(minutes=max_age_minutes)

    def get_or_fetch(self, cache_key: str, path: str, max_age_minutes: int) -> dict | list:
        if self._is_fresh(cache_key, max_age_minutes):
            return self._read_cache_data(cache_key)

        data = self.fetch_json(path)
        self._write_cache(cache_key, data)
        return data

    def get_cached_only(self, cache_key: str) -> dict | list:
        return self._read_cache_data(cache_key)

    def get_bootstrap(self, use_cache_only: bool = False) -> dict:
        if use_cache_only:
            return self.get_cached_only("bootstrap-static")
        return self.get_or_fetch("bootstrap-static", "/bootstrap-static/", 180)

    def get_fixtures(self, use_cache_only: bool = False) -> list[dict]:
        if use_cache_only:
            return self.get_cached_only("fixtures")
        return self.get_or_fetch("fixtures", "/fixtures/", 180)

    def get_element_summary(self, element_id: int, use_cache_only: bool = False) -> dict:
        cache_key = f"element-summary-{element_id}"
        if use_cache_only:
            return self.get_cached_only(cache_key)
        return self.get_or_fetch(cache_key, f"/element-summary/{element_id}/", 180)

    def get_event_live(self, event_id: int, use_cache_only: bool = False) -> dict:
        cache_key = f"event-live-{event_id}"
        if use_cache_only:
            return self.get_cached_only(cache_key)
        return self.get_or_fetch(cache_key, f"/event/{event_id}/live/", 60)

    def refresh_core_data(self) -> dict:
        bootstrap = self.fetch_json("/bootstrap-static/")
        fixtures = self.fetch_json("/fixtures/")
        self._write_cache("bootstrap-static", bootstrap)
        self._write_cache("fixtures", fixtures)
        return bootstrap

    def refresh_player_summaries(self, element_ids: list[int]) -> None:
        for element_id in sorted(set(element_ids)):
            summary = self.fetch_json(f"/element-summary/{element_id}/")
            self._write_cache(f"element-summary-{element_id}", summary)

    def refresh_event_live(self, event_id: int) -> None:
        event_live = self.fetch_json(f"/event/{event_id}/live/")
        self._write_cache(f"event-live-{event_id}", event_live)

    def get_cache_status(self) -> dict:
        try:
            bootstrap_payload = self._read_cache_payload("bootstrap-static")
            return {
                "available": True,
                "cached_at": bootstrap_payload["cached_at"],
            }
        except CacheMissError:
            return {
                "available": False,
                "cached_at": None,
            }
