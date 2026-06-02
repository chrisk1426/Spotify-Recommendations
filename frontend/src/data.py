# ============================================
# Final Project
# Name: Tyler Bruno
# Course: Dartmouth CS 61 Spring 2026
# ============================================

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from models import AudioFeatures, MoodProfile, Recommendation, Track


API_BASE_URL = os.environ.get("SPOTIFY_API_URL", "http://127.0.0.1:5000").rstrip("/")
API_TIMEOUT = float(os.environ.get("SPOTIFY_API_TIMEOUT", "8"))


class ApiError(RuntimeError):
    pass


def request_json(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    query = ""
    if params:
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        if clean_params:
            query = "?" + urlencode(clean_params)

    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{API_BASE_URL}{path}{query}",
        data=body,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urlopen(request, timeout=API_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except HTTPError as error:
        raise ApiError(_error_message(error)) from error
    except URLError as error:
        raise ApiError(f"Backend unavailable at {API_BASE_URL}: {error.reason}") from error
    except TimeoutError as error:
        raise ApiError(f"Backend request timed out at {API_BASE_URL}") from error

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ApiError(f"Backend returned invalid JSON for {path}") from error


def _error_message(error: HTTPError) -> str:
    try:
        body = error.read().decode("utf-8")
        data = json.loads(body)
    except Exception:
        return f"HTTP {error.code}: {error.reason}"

    if isinstance(data, dict) and data.get("error"):
        return str(data["error"])
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"])
    return f"HTTP {error.code}: {error.reason}"


def list_tracks(query: str = "", limit: int = 50) -> list[Track]:
    rows = request_json("GET", "/tracks/", {"q": query, "limit": limit})
    return [track_from_row(row) for row in rows]


def get_track(track_id: int) -> Track:
    return track_from_row(request_json("GET", f"/tracks/{track_id}"))


def get_recommendations(track_id: int, limit: int = 10, user_id: int | None = None) -> list[Recommendation]:
    data = request_json("GET", f"/recommendations/{track_id}", {"limit": limit, "user_id": user_id})
    return [
        Recommendation(track=track_from_row(row), score=_float(row, "SimilarityScore"))
        for row in data.get("recommendations", [])
    ]


def get_recommendation_history(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    rows = request_json("GET", f"/recommendations/history/{user_id}", {"limit": limit})
    for row in rows:
        row["track"] = track_from_row(row)
    return rows


def clear_recommendation_history(user_id: int) -> dict[str, Any]:
    return request_json("DELETE", f"/recommendations/history/{user_id}")


def list_mood_profiles() -> list[MoodProfile]:
    rows = request_json("GET", "/mood/profiles")
    return [mood_from_row(row) for row in rows]


def search_mood(mood_name: str, limit: int = 50) -> tuple[MoodProfile | None, list[Track]]:
    data = request_json("GET", "/mood/search", {"mood": mood_name, "limit": limit})
    profile_data = data.get("mood_profile")
    profile = None
    if isinstance(profile_data, dict):
        profile = MoodProfile(
            mood_id=_int(profile_data, "id"),
            name=str(profile_data.get("name", mood_name)),
        )
    return profile, [track_from_row(row) for row in data.get("tracks", [])]


def login(username: str, password: str) -> dict[str, Any]:
    return request_json("POST", "/auth/login", payload={"username": username, "password": password})


def register(username: str, password: str) -> dict[str, Any]:
    return request_json("POST", "/auth/register", payload={"username": username, "password": password})


def get_profile(user_id: int) -> dict[str, Any]:
    return request_json("GET", f"/auth/profile/{user_id}")


def list_user_playlists(user_id: int) -> list[dict[str, Any]]:
    return request_json("GET", f"/playlists/user/{user_id}")


def get_playlist_tracks(playlist_id: int) -> list[Track]:
    rows = request_json("GET", f"/playlists/{playlist_id}/tracks")
    return [track_from_row(row) for row in rows]


def create_playlist(
    user_id: int,
    name: str,
    mood_profile_id: int | None = None,
    track_ids: list[int] | None = None,
) -> dict[str, Any]:
    return request_json(
        "POST",
        "/playlists/",
        payload={
            "user_id": user_id,
            "name": name,
            "mood_profile_id": mood_profile_id,
            "track_ids": track_ids or [],
        },
    )


def add_playlist_track(playlist_id: int, user_id: int, track_id: int) -> dict[str, Any]:
    return request_json(
        "POST",
        f"/playlists/{playlist_id}/tracks",
        payload={"user_id": user_id, "track_id": track_id},
    )


def remove_playlist_track(playlist_id: int, user_id: int, track_id: int) -> dict[str, Any]:
    return request_json(
        "DELETE",
        f"/playlists/{playlist_id}/tracks/{track_id}",
        {"user_id": user_id},
    )


def delete_playlist(playlist_id: int, user_id: int) -> dict[str, Any]:
    return request_json("DELETE", f"/playlists/{playlist_id}", {"user_id": user_id})


def generate_playlist(user_id: int, mood_profile_id: int, name: str, limit: int = 20) -> dict[str, Any]:
    return request_json(
        "POST",
        "/playlists/generate",
        payload={
            "user_id": user_id,
            "mood_profile_id": mood_profile_id,
            "name": name,
            "limit": limit,
        },
    )


def analytics_summary() -> dict[str, Any]:
    return request_json("GET", "/analytics/summary")


def energetic_genres(limit: int = 20) -> list[dict[str, Any]]:
    return request_json("GET", "/analytics/energetic-genres", {"limit": limit})


def valence_by_genre(limit: int = 20) -> list[dict[str, Any]]:
    return request_json("GET", "/analytics/valence-by-genre", {"limit": limit})


def popularity_by_genre(limit: int = 20) -> list[dict[str, Any]]:
    return request_json("GET", "/analytics/popularity-by-genre", {"limit": limit})


def bpm_distribution(bucket_size: int = 10) -> list[dict[str, Any]]:
    return request_json("GET", "/analytics/bpm-distribution", {"bucket_size": bucket_size})


def popularity_vs_danceability(limit: int = 100) -> list[dict[str, Any]]:
    return request_json("GET", "/analytics/popularity-vs-danceability", {"limit": limit})


def list_artists(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    return request_json("GET", "/artists/", {"q": query, "limit": limit})


def get_artist(artist_id: int) -> dict[str, Any]:
    return request_json("GET", f"/artists/{artist_id}")


def list_albums(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    return request_json("GET", "/albums/", {"q": query, "limit": limit})


def get_album_tracks(album_id: int) -> list[Track]:
    rows = request_json("GET", f"/albums/{album_id}/tracks")
    return [track_from_row(row) for row in rows]


def list_genres() -> list[dict[str, Any]]:
    return request_json("GET", "/genres/")


def get_genre_tracks(genre_id: int) -> list[Track]:
    rows = request_json("GET", f"/genres/{genre_id}/tracks")
    return [track_from_row(row) for row in rows]


def track_from_row(row: dict[str, Any]) -> Track:
    artists = _names(row.get("Artists"))
    genres = _names(row.get("Genres"))
    return Track(
        track_id=_int(row, "TrackID", "track_id"),
        spotify_track_id=_str_or_none(row.get("SpotifyTrackID")),
        name=str(row.get("TrackName") or row.get("track_name") or "Unknown track"),
        artists=artists,
        album=str(row.get("AlbumName") or ""),
        genres=genres,
        duration_ms=_int(row, "Duration", default=0),
        popularity=_int(row, "Popularity", default=0),
        explicit=bool(_int(row, "IsExplicit", default=0)),
        features=AudioFeatures(
            danceability=_float(row, "Danceability"),
            energy=_float(row, "Energy"),
            tempo=_float(row, "Tempo"),
            acousticness=_float(row, "Acousticness"),
            valence=_float(row, "Valence"),
            loudness=_float(row, "Loudness"),
            speechiness=_float(row, "Speechiness"),
            instrumentalness=_float(row, "Instrumentalness"),
            liveness=_float(row, "Liveness"),
        ),
    )


def mood_from_row(row: dict[str, Any]) -> MoodProfile:
    return MoodProfile(
        mood_id=_int(row, "MoodProfileID"),
        name=str(row.get("MoodProfileName") or ""),
        min_danceability=_optional_float(row, "MinDanceability"),
        max_danceability=_optional_float(row, "MaxDanceability"),
        min_energy=_optional_float(row, "MinEnergy"),
        max_energy=_optional_float(row, "MaxEnergy"),
        min_loudness=_optional_float(row, "MinLoudness"),
        max_loudness=_optional_float(row, "MaxLoudness"),
        min_speechiness=_optional_float(row, "MinSpeechiness"),
        max_speechiness=_optional_float(row, "MaxSpeechiness"),
        min_acousticness=_optional_float(row, "MinAcousticness"),
        max_acousticness=_optional_float(row, "MaxAcousticness"),
        min_instrumentalness=_optional_float(row, "MinInstrumentalness"),
        max_instrumentalness=_optional_float(row, "MaxInstrumentalness"),
        min_liveness=_optional_float(row, "MinLiveness"),
        max_liveness=_optional_float(row, "MaxLiveness"),
        min_valence=_optional_float(row, "MinValence"),
        max_valence=_optional_float(row, "MaxValence"),
        min_tempo=_optional_float(row, "MinTempo"),
        max_tempo=_optional_float(row, "MaxTempo"),
    )


def format_duration(milliseconds: int) -> str:
    minutes, seconds = divmod(round(milliseconds / 1000), 60)
    return f"{minutes}:{seconds:02d}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.0f}%"


def _names(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value if item is not None)
    if isinstance(value, tuple):
        return tuple(str(item) for item in value if item is not None)
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _int(row: dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
    return default


def _float(row: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
    return default


def _optional_float(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
