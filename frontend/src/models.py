# ============================================
# Final Project
# Name: Tyler Bruno
# Course: Dartmouth CS 61 Spring 2026
# ============================================

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioFeatures:
    danceability: float = 0.0
    energy: float = 0.0
    tempo: float = 0.0
    acousticness: float = 0.0
    valence: float = 0.0
    loudness: float = 0.0
    speechiness: float = 0.0
    instrumentalness: float = 0.0
    liveness: float = 0.0


@dataclass(frozen=True)
class Track:
    track_id: int
    name: str
    artists: tuple[str, ...]
    album: str
    genres: tuple[str, ...]
    duration_ms: int
    popularity: int
    explicit: bool
    features: AudioFeatures
    spotify_track_id: str | None = None

    @property
    def duration_seconds(self) -> int:
        return round(self.duration_ms / 1000)

    @property
    def spotify_url(self) -> str:
        if not self.spotify_track_id:
            return "https://open.spotify.com/"
        return f"https://open.spotify.com/track/{self.spotify_track_id}"


@dataclass(frozen=True)
class MoodProfile:
    mood_id: int
    name: str
    min_danceability: float | None = None
    max_danceability: float | None = None
    min_energy: float | None = None
    max_energy: float | None = None
    min_loudness: float | None = None
    max_loudness: float | None = None
    min_speechiness: float | None = None
    max_speechiness: float | None = None
    min_acousticness: float | None = None
    max_acousticness: float | None = None
    min_instrumentalness: float | None = None
    max_instrumentalness: float | None = None
    min_liveness: float | None = None
    max_liveness: float | None = None
    min_valence: float | None = None
    max_valence: float | None = None
    min_tempo: float | None = None
    max_tempo: float | None = None


@dataclass(frozen=True)
class Recommendation:
    track: Track
    score: float
