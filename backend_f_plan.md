# Backend Final Implementation Plan

## Overview

Six things left to implement:
1. `mood.py` — mood profile listing and track search by mood
2. `recommendations.py` — audio-feature similarity + genre overlap + popularity scoring, with RecommendationHistory logging
3. `analytics.py` — aggregate dataset queries
4. `albums.py` — album lookup endpoints
5. `add_indexes_constraints.sql` — performance indexes and data integrity constraints
6. `app.py` update — register the four new blueprints

---

## 1. `mood.py`

**Blueprint prefix:** `/mood`

### Endpoints

#### `GET /mood/profiles`
- Query: `SELECT * FROM MoodProfiles ORDER BY MoodProfileName`
- Returns all 7 preconfigured mood profiles with their min/max ranges
- Used by the frontend to let users pick a mood before searching or generating a playlist

#### `GET /mood/search?mood=<name>&limit=<n>`
- Accepts a mood name (e.g. `gym`, `study`, `happy`)
- Looks up the MoodProfile row by name
- Queries `AudioFeatures` with `BETWEEN` on each non-NULL min/max column
- Joins back to `Tracks`, `Albums`, `Artists` (GROUP_CONCAT), `Genres` (GROUP_CONCAT)
- Orders by `Tracks.Popularity DESC`
- Returns up to `limit` tracks (default 50)

**BETWEEN null handling:** Several mood profiles have NULL for some min/max pairs (e.g. gym has NULL for liveness). The query must skip those columns rather than filtering on NULL. Build the WHERE clause dynamically in Python based on which fields are non-NULL in the mood profile row.

#### `GET /mood/profiles/<int:mood_profile_id>`
- Returns a single mood profile by ID
- Useful for the frontend to display what ranges a mood uses

---

## 2. `recommendations.py`

**Blueprint prefix:** `/recommendations`

### Scoring Formula

Given a seed `TrackID`, score every other track using a weighted formula computed in SQL:

```
score = (
    0.25 * (1 - ABS(seed.Energy       - cand.Energy))       +
    0.20 * (1 - ABS(seed.Danceability  - cand.Danceability)) +
    0.20 * (1 - ABS(seed.Valence       - cand.Valence))      +
    0.15 * (1 - ABS(seed.Acousticness  - cand.Acousticness)) +
    0.10 * (1 - ABS(seed.Tempo/250     - cand.Tempo/250))    +
    0.10 * (genre_overlap / total_seed_genres)
) * (0.7 + 0.3 * cand.Popularity/100)
```

- All audio feature differences are already 0–1 so (1 - ABS(diff)) gives similarity directly
- Tempo is normalized by dividing by 250 (rough max BPM in dataset) before differencing
- Genre overlap = count of genres shared between seed and candidate / seed's total genre count (0 if seed has no genres). If candidate has 0 shared genres, genre term = 0
- Popularity multiplier scales the raw similarity score so popular songs rank higher, but a song with score 1.0 at pop 0 still beats a score 0.5 at pop 100 (roughly — the 0.7 floor keeps it audio-feature-driven)
- Final score range: approximately 0.0 – 1.0

### Endpoints

#### `GET /recommendations/<int:track_id>?limit=<n>&user_id=<id>`
- `track_id`: the seed track to find similar songs for
- `user_id` (optional): if provided, logs results to `RecommendationHistory`
- `limit`: how many results to return (default 10, max 50)

**Logic:**
1. Fetch seed track's `AudioFeatures` and its genres from `TrackGenres`
2. Run the scoring query against all other tracks (excluding seed)
3. If `user_id` provided, open a transaction and INSERT into `RecommendationHistory` for each returned track, then commit. Rollback if insert fails but still return results (log failure, don't break the endpoint)
4. Return ranked list with `TrackID`, `TrackName`, `Artists`, `Genres`, `Popularity`, and `SimilarityScore`

#### `GET /recommendations/history/<int:user_id>?limit=<n>`
- Returns the user's past recommendation history
- Joins `RecommendationHistory` → `Tracks` → `Artists`
- Orders by `GeneratedAt DESC`
- Default limit 50

#### `DELETE /recommendations/history/<int:user_id>`
- Clears a user's full recommendation history
- Uses a transaction (single DELETE, but wrapped for consistency)

---

## 3. `analytics.py`

**Blueprint prefix:** `/analytics`

All queries are read-only aggregations over the full dataset. No transactions needed.

### Endpoints

#### `GET /analytics/energetic-genres?limit=<n>`
- Joins `TrackGenres → Genres → AudioFeatures`
- Groups by `GenreName`
- Returns `AVG(Energy) AS AvgEnergy`, `COUNT(*) AS TrackCount`
- Orders by `AvgEnergy DESC`
- Default limit 20

#### `GET /analytics/valence-by-genre?limit=<n>`
- Same join pattern
- Returns `AVG(Valence) AS AvgValence` per genre
- Orders by `AvgValence DESC`
- Default limit 20

#### `GET /analytics/bpm-distribution?buckets=<n>`
- Groups tracks into BPM buckets using `FLOOR(Tempo / bucket_size) * bucket_size`
- Default bucket size = 10 BPM (i.e. 60–69, 70–79, …)
- Returns `BucketMin`, `BucketMax`, `TrackCount`
- Orders by `BucketMin ASC`
- `buckets` param controls bucket size (not count), default 10

#### `GET /analytics/popularity-by-genre?limit=<n>`
- Groups by genre, returns `AVG(Popularity) AS AvgPopularity`, `COUNT(*) AS TrackCount`
- Orders by `AvgPopularity DESC`
- Default limit 20

#### `GET /analytics/popularity-vs-danceability`
- Returns a scatter-friendly dataset: `Popularity`, `Danceability`, `TrackName` for a random sample of tracks
- Uses `ORDER BY RAND() LIMIT 500` so the response stays small
- Frontend can plot this as a scatter chart

#### `GET /analytics/summary`
- Returns a quick overview object:
  - Total tracks, total artists, total albums, total genres
  - Overall avg energy, avg valence, avg tempo, avg popularity
  - Single query using `SELECT COUNT(*), AVG(...)` from Tracks JOIN AudioFeatures

---

## 4. `albums.py`

**Blueprint prefix:** `/albums`

Simple read-only endpoints. No transactions needed (albums are populated by the loader and not user-editable).

### Endpoints

#### `GET /albums/<int:album_id>`
- Returns `AlbumID`, `AlbumName`, and aggregate stats: `TrackCount`, `AVG(Popularity)`
- Joins `Albums → Tracks`

#### `GET /albums/<int:album_id>/tracks`
- Returns all tracks in the album
- Joins `Tracks → AudioFeatures → TrackArtists → Artists → TrackGenres → Genres`
- Same full-detail shape as the tracks route GET by ID
- Orders by `Popularity DESC`

#### `GET /albums/?q=<search>&limit=<n>`
- Search albums by name (`LIKE %q%`)
- Returns `AlbumID`, `AlbumName`, `TrackCount`
- Default limit 50

---

## 5. `add_indexes_constraints.sql`

New file, run once against the live `spotify_explorer` database after the schema and data are loaded. Uses `IF NOT EXISTS` for indexes (MySQL 8.0+) and `INFORMATION_SCHEMA` guards for constraints so it is safe to re-run.

### Unique Constraints

| Table | Column(s) | Reason |
|---|---|---|
| `Users` | `UserName` | Prevent duplicate accounts — nothing enforces this today |
| `MoodProfiles` | `MoodProfileName` | Mood names must be unique (referenced by name in mood search) |

### CHECK Constraints

| Table | Constraint | Reason |
|---|---|---|
| `Tracks` | `Popularity BETWEEN 0 AND 100` | Business rule from plan; prevents bad imports |
| `AudioFeatures` | `Danceability BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Energy BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Speechiness BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Acousticness BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Instrumentalness BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Liveness BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Valence BETWEEN 0 AND 1` | Spotify spec |
| `AudioFeatures` | `Tempo >= 0` | Cannot have negative BPM |
| `Users` | `IsAdmin IN (0, 1)` | Boolean guard |

### Performance Indexes

| Table | Index columns | Why needed |
|---|---|---|
| `Tracks` | `(Popularity DESC)` | ORDER BY Popularity DESC appears in nearly every route |
| `Tracks` | `(AlbumID)` | FK join used in every full-detail track query |
| `Playlists` | `(UserID)` | GET /playlists/user/<id> does a WHERE UserID = ? |
| `Playlists` | `(MoodProfileID)` | FK join for mood-based playlist queries |
| `TrackArtists` | `(ArtistID)` | Reverse lookup: all tracks by an artist |
| `TrackGenres` | `(GenreID)` | Reverse lookup: all tracks in a genre (genres route) |
| `RecommendationHistory` | `(UserID)` | History fetch by user |
| `RecommendationHistory` | `(TrackID)` | ON DELETE cascade lookup; used in track delete |
| `RecommendationHistory` | `(GeneratedAt DESC)` | Order history most-recent-first |
| `AudioFeatures` | `(Energy)` | Mood search BETWEEN filter |
| `AudioFeatures` | `(Danceability)` | Mood search BETWEEN filter |
| `AudioFeatures` | `(Valence)` | Mood search BETWEEN filter |
| `AudioFeatures` | `(Tempo)` | Mood search BETWEEN filter |

> Note: MySQL can only use one index per table scan per query. For mood queries that filter on 4–5 columns simultaneously, a single composite index like `(Energy, Danceability, Valence, Tempo)` would be more efficient than four separate ones. The plan is to add both the individual indexes (useful for single-column analytics queries) and one composite index for the multi-column mood/generate-playlist scan.

**Composite index for mood filtering:**
- `AudioFeatures (Energy, Danceability, Valence, Tempo)` — covers the most common multi-column range filter

---

## 6. `app.py` Updates

Register the four new blueprints:

```python
from routes.mood import mood_bp
from routes.recommendations import recommendations_bp
from routes.analytics import analytics_bp
from routes.albums import albums_bp

app.register_blueprint(mood_bp, url_prefix='/mood')
app.register_blueprint(recommendations_bp, url_prefix='/recommendations')
app.register_blueprint(analytics_bp, url_prefix='/analytics')
app.register_blueprint(albums_bp, url_prefix='/albums')
```

---

## Implementation Order

1. `add_indexes_constraints.sql` — foundation, should exist before heavy queries run
2. `albums.py` — simplest, good warm-up, no complex logic
3. `mood.py` — straightforward range queries, needed by recommendations context
4. `analytics.py` — pure read aggregates, independent of other new routes
5. `recommendations.py` — most complex (scoring formula + history transaction)
6. `app.py` — register all blueprints last, after all routes are written

---

## Open Questions / Decisions to Confirm

- **Recommendation history write failure:** Should a failed INSERT into `RecommendationHistory` return a 500 or silently succeed (return results but skip logging)? Plan assumes silent skip to keep the endpoint robust.
- **Recommendation scoring performance:** The scoring query does a full table scan of ~90k AudioFeatures rows on every request. An acceptable tradeoff for a class project, but we could add a `LIMIT` on candidates pre-filtered by genre overlap first if it's too slow.
- **Analytics caching:** The plan doc mentions admin users can refresh cached analytics. For now, all analytics endpoints query live — no caching layer. Can revisit if queries are slow.
- **Albums write endpoints:** The loader owns album creation. No POST/PUT/DELETE on albums is planned unless needed.
