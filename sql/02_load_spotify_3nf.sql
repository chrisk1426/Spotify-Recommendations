/*
  Spotify Music Explorer 3NF loader
  ----------------------------------
  Use this AFTER forward-engineering spotify_music_explorer-1.mwb into MySQL.

  What it does:
    1. Loads dataset.csv into a staging table.
    2. De-duplicates the CSV to one Tracks/AudioFeatures row per Spotify track_id.
    3. Splits semicolon-separated artists into Artists + TrackArtists.
    4. Converts repeated genre strings into Genres + TrackGenres.
    5. Rebuilds the catalog tables in 3NF.

  IMPORTANT:
    - The .mwb file is a Workbench model, not a database data file. Run this against
      the MySQL schema generated from the .mwb.
    - This script truncates/rebuilds the catalog and demo/user tables. Run it on a
      fresh project database or backup first.
    - Edit the LOAD DATA path below to point to dataset.csv on YOUR machine.
    - If LOCAL INFILE is disabled, enable it in your MySQL connection settings.
*/

USE spotify_explorer;

SET NAMES utf8mb4;
SET SESSION sql_mode = REPLACE(REPLACE(REPLACE(@@SESSION.sql_mode, 'NO_BACKSLASH_ESCAPES,', ''), ',NO_BACKSLASH_ESCAPES', ''), 'NO_BACKSLASH_ESCAPES', '');

-- ---------------------------------------------------------------------------
-- 0) Make the live database match the project needs/data.
--    Your current .mwb Tracks table has TrackID but no Spotify track_id column.
--    The project plan needs the Spotify id for links/search, so we add it here.
-- ---------------------------------------------------------------------------

SET @current_schema := DATABASE();

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE Tracks ADD COLUMN SpotifyTrackID VARCHAR(32) NULL AFTER TrackID',
    'SELECT ''SpotifyTrackID column already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @current_schema
    AND TABLE_NAME = 'Tracks'
    AND COLUMN_NAME = 'SpotifyTrackID'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Track names in the CSV can be longer than 255 chars; avoid truncation/import errors.
ALTER TABLE Tracks MODIFY COLUMN TrackName VARCHAR(512) NOT NULL;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE Tracks ADD UNIQUE INDEX uq_tracks_spotifytrackid (SpotifyTrackID)',
    'SELECT ''uq_tracks_spotifytrackid already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @current_schema
    AND TABLE_NAME = 'Tracks'
    AND INDEX_NAME = 'uq_tracks_spotifytrackid'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------------
-- 1) Rebuild project data tables.
-- ---------------------------------------------------------------------------

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE RecommendationHistory;
TRUNCATE TABLE PlaylistTracks;
TRUNCATE TABLE Playlists;
TRUNCATE TABLE TrackArtists;
TRUNCATE TABLE TrackGenres;
TRUNCATE TABLE AudioFeatures;
TRUNCATE TABLE Tracks;
TRUNCATE TABLE Albums;
TRUNCATE TABLE Artists;
TRUNCATE TABLE Genres;
TRUNCATE TABLE MoodProfiles;
TRUNCATE TABLE Users;
SET FOREIGN_KEY_CHECKS = 1;

DROP TABLE IF EXISTS stg_spotify_raw;
DROP TABLE IF EXISTS stg_spotify_clean;
DROP TABLE IF EXISTS stg_track_choice;
DROP TABLE IF EXISTS stg_artist_split;
DROP TABLE IF EXISTS stg_album_map;
DROP TABLE IF EXISTS stg_artist_map;
DROP TABLE IF EXISTS stg_genre_map;
DROP TABLE IF EXISTS stg_track_map;

CREATE TABLE stg_spotify_raw (
  SourceRowNum INT NULL,
  SpotifyTrackID VARCHAR(32) NULL,
  ArtistsRaw TEXT NULL,
  AlbumName VARCHAR(512) NULL,
  TrackName VARCHAR(512) NULL,
  Popularity INT NULL,
  DurationMs INT NULL,
  IsExplicit TINYINT(1) NULL,
  Danceability FLOAT NULL,
  Energy FLOAT NULL,
  SpotifyKey INT NULL,
  Loudness FLOAT NULL,
  SpotifyMode INT NULL,
  Speechiness FLOAT NULL,
  Acousticness FLOAT NULL,
  Instrumentalness FLOAT NULL,
  Liveness FLOAT NULL,
  Valence FLOAT NULL,
  Tempo FLOAT NULL,
  TimeSignature INT NULL,
  TrackGenre VARCHAR(100) NULL,
  KEY idx_stg_spotify_id (SpotifyTrackID),
  KEY idx_stg_genre (TrackGenre)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

-- CHANGE THIS PATH before running in MySQL Workbench.
-- On Windows, use forward slashes, e.g. C:/Users/you/Downloads/dataset.csv
LOAD DATA LOCAL INFILE '/absolute/path/to/dataset.csv'
INTO TABLE stg_spotify_raw
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@SourceRowNum, @SpotifyTrackID, @ArtistsRaw, @AlbumName, @TrackName,
 @Popularity, @DurationMs, @ExplicitRaw, @Danceability, @Energy, @Key,
 @Loudness, @Mode, @Speechiness, @Acousticness, @Instrumentalness,
 @Liveness, @Valence, @Tempo, @TimeSignature, @TrackGenre)
SET
  SourceRowNum = NULLIF(@SourceRowNum, ''),
  SpotifyTrackID = NULLIF(TRIM(@SpotifyTrackID), ''),
  ArtistsRaw = NULLIF(TRIM(@ArtistsRaw), ''),
  AlbumName = NULLIF(TRIM(@AlbumName), ''),
  TrackName = NULLIF(TRIM(@TrackName), ''),
  Popularity = NULLIF(@Popularity, ''),
  DurationMs = NULLIF(@DurationMs, ''),
  IsExplicit = CASE
                 WHEN LOWER(TRIM(@ExplicitRaw)) IN ('true', '1', 'yes') THEN 1
                 ELSE 0
               END,
  Danceability = NULLIF(@Danceability, ''),
  Energy = NULLIF(@Energy, ''),
  SpotifyKey = NULLIF(@Key, ''),
  Loudness = NULLIF(@Loudness, ''),
  SpotifyMode = NULLIF(@Mode, ''),
  Speechiness = NULLIF(@Speechiness, ''),
  Acousticness = NULLIF(@Acousticness, ''),
  Instrumentalness = NULLIF(@Instrumentalness, ''),
  Liveness = NULLIF(@Liveness, ''),
  Valence = NULLIF(@Valence, ''),
  Tempo = NULLIF(@Tempo, ''),
  TimeSignature = NULLIF(@TimeSignature, ''),
  TrackGenre = NULLIF(TRIM(@TrackGenre), '');

-- Remove rows that violate the project import rule: valid id, title, artist, album, genre.
CREATE TABLE stg_spotify_clean AS
SELECT *
FROM stg_spotify_raw
WHERE SpotifyTrackID IS NOT NULL
  AND TrackName IS NOT NULL
  AND ArtistsRaw IS NOT NULL
  AND AlbumName IS NOT NULL
  AND TrackGenre IS NOT NULL;

ALTER TABLE stg_spotify_clean
  ADD KEY idx_clean_spotify_id (SpotifyTrackID),
  ADD KEY idx_clean_album (AlbumName),
  ADD KEY idx_clean_genre (TrackGenre);

-- Pick one canonical metadata/audio-feature row per Spotify track.
-- If a track appears under multiple genres, its genres are preserved later in TrackGenres.
CREATE TABLE stg_track_choice AS
SELECT *
FROM (
  SELECT
    c.*,
    ROW_NUMBER() OVER (
      PARTITION BY c.SpotifyTrackID
      ORDER BY c.Popularity DESC, c.SourceRowNum ASC
    ) AS rn
  FROM stg_spotify_clean c
) ranked
WHERE rn = 1;

ALTER TABLE stg_track_choice
  ADD UNIQUE KEY uq_choice_spotify_id (SpotifyTrackID),
  ADD KEY idx_choice_album (AlbumName);

-- Deterministic surrogate-key maps. These populate your INT primary keys while
-- preserving the CSV SpotifyTrackID inside Tracks.
CREATE TABLE stg_album_map AS
SELECT
  ROW_NUMBER() OVER (ORDER BY AlbumName) AS AlbumID,
  AlbumName
FROM (
  SELECT DISTINCT AlbumName
  FROM stg_spotify_clean
) x;

ALTER TABLE stg_album_map
  ADD PRIMARY KEY (AlbumID),
  ADD UNIQUE KEY uq_album_name (AlbumName);

CREATE TABLE stg_genre_map AS
SELECT
  ROW_NUMBER() OVER (ORDER BY TrackGenre) AS GenreID,
  TrackGenre AS GenreName
FROM (
  SELECT DISTINCT TrackGenre
  FROM stg_spotify_clean
) x;

ALTER TABLE stg_genre_map
  ADD PRIMARY KEY (GenreID),
  ADD UNIQUE KEY uq_genre_name (GenreName);

-- Split semicolon-separated artists into one row per artist per Spotify track.
CREATE TABLE stg_artist_split AS
WITH RECURSIVE artist_cte AS (
  SELECT
    SpotifyTrackID,
    CAST(TRIM(SUBSTRING_INDEX(ArtistsRaw, ';', 1)) AS CHAR(255)) AS ArtistName,
    CAST(
      CASE
        WHEN LOCATE(';', ArtistsRaw) > 0 THEN SUBSTRING(ArtistsRaw, LOCATE(';', ArtistsRaw) + 1)
        ELSE ''
      END AS CHAR(2048)
    ) AS remaining_artists
  FROM stg_spotify_clean

  UNION ALL

  SELECT
    SpotifyTrackID,
    CAST(TRIM(SUBSTRING_INDEX(remaining_artists, ';', 1)) AS CHAR(255)) AS ArtistName,
    CAST(
      CASE
        WHEN LOCATE(';', remaining_artists) > 0 THEN SUBSTRING(remaining_artists, LOCATE(';', remaining_artists) + 1)
        ELSE ''
      END AS CHAR(2048)
    ) AS remaining_artists
  FROM artist_cte
  WHERE remaining_artists <> ''
)
SELECT DISTINCT SpotifyTrackID, ArtistName
FROM artist_cte
WHERE ArtistName IS NOT NULL AND ArtistName <> '';

ALTER TABLE stg_artist_split
  MODIFY SpotifyTrackID VARCHAR(32) NOT NULL,
  MODIFY ArtistName VARCHAR(255) NOT NULL,
  ADD PRIMARY KEY (SpotifyTrackID, ArtistName),
  ADD KEY idx_artist_split_name (ArtistName);

CREATE TABLE stg_artist_map AS
SELECT
  ROW_NUMBER() OVER (ORDER BY ArtistName) AS ArtistID,
  ArtistName
FROM (
  SELECT DISTINCT ArtistName
  FROM stg_artist_split
) x;

ALTER TABLE stg_artist_map
  ADD PRIMARY KEY (ArtistID),
  ADD UNIQUE KEY uq_artist_name (ArtistName);

CREATE TABLE stg_track_map AS
SELECT
  ROW_NUMBER() OVER (ORDER BY SpotifyTrackID) AS TrackID,
  SpotifyTrackID
FROM (
  SELECT DISTINCT SpotifyTrackID
  FROM stg_spotify_clean
) x;

ALTER TABLE stg_track_map
  ADD PRIMARY KEY (TrackID),
  ADD UNIQUE KEY uq_track_map_spotify_id (SpotifyTrackID);

-- ---------------------------------------------------------------------------
-- 2) Insert normalized data.
-- ---------------------------------------------------------------------------

INSERT INTO Albums (AlbumID, AlbumName)
SELECT AlbumID, AlbumName
FROM stg_album_map
ORDER BY AlbumID;

INSERT INTO Artists (ArtistID, ArtistName)
SELECT ArtistID, ArtistName
FROM stg_artist_map
ORDER BY ArtistID;

INSERT INTO Genres (GenreID, GenreName)
SELECT GenreID, GenreName
FROM stg_genre_map
ORDER BY GenreID;

INSERT INTO Tracks (
  TrackID, SpotifyTrackID, TrackName, Duration, Popularity, IsExplicit, AlbumID
)
SELECT
  tm.TrackID,
  tc.SpotifyTrackID,
  tc.TrackName,
  tc.DurationMs,
  tc.Popularity,
  tc.IsExplicit,
  am.AlbumID
FROM stg_track_choice tc
JOIN stg_track_map tm
  ON tm.SpotifyTrackID = tc.SpotifyTrackID
JOIN stg_album_map am
  ON am.AlbumName = tc.AlbumName
ORDER BY tm.TrackID;

INSERT INTO AudioFeatures (
  TrackID, Danceability, Energy, `Key`, Loudness, `Mode`, Speechiness,
  Acousticness, Instrumentalness, Liveness, Valence, Tempo, TimeSignature
)
SELECT
  tm.TrackID,
  tc.Danceability,
  tc.Energy,
  tc.SpotifyKey,
  tc.Loudness,
  tc.SpotifyMode,
  tc.Speechiness,
  tc.Acousticness,
  tc.Instrumentalness,
  tc.Liveness,
  tc.Valence,
  tc.Tempo,
  tc.TimeSignature
FROM stg_track_choice tc
JOIN stg_track_map tm
  ON tm.SpotifyTrackID = tc.SpotifyTrackID
ORDER BY tm.TrackID;

INSERT INTO TrackArtists (TrackID, ArtistID)
SELECT DISTINCT
  tm.TrackID,
  am.ArtistID
FROM stg_artist_split s
JOIN stg_track_map tm
  ON tm.SpotifyTrackID = s.SpotifyTrackID
JOIN stg_artist_map am
  ON am.ArtistName = s.ArtistName;

INSERT INTO TrackGenres (TrackID, GenreID)
SELECT DISTINCT
  tm.TrackID,
  gm.GenID
FROM (
  SELECT DISTINCT SpotifyTrackID, TrackGenre
  FROM stg_spotify_clean
) tg
JOIN stg_track_map tm
  ON tm.SpotifyTrackID = tg.SpotifyTrackID
JOIN (
  SELECT GenreID AS GenID, GenreName
  FROM stg_genre_map
) gm
  ON gm.GenreName = tg.TrackGenre;

-- Optional starter app data: one admin user and preconfigured mood profiles.
-- Password value is a placeholder bcrypt-looking string; replace it in the app.
INSERT INTO Users (UserID, UserName, Password, IsAdmin)
VALUES
  (1, 'admin', '$2b$12$C6UzMDM.H6dfI/f/IKcEeO8G4z8A7QLQd6dI5MnN4uV1uE0q5eVwS', 1);

INSERT INTO MoodProfiles (
  MoodProfileID, MoodProfileName,
  MinDanceability, MaxDanceability, MinEnergy, MaxEnergy,
  MinLoudness, MaxLoudness, MinSpeechiness, MaxSpeechiness,
  MinAcousticness, MaxAcousticness, MinInstrumentalness, MaxInstrumentalness,
  MinLiveness, MaxLiveness, MinValence, MaxValence, MinTempo, MaxTempo
)
VALUES
  (1, 'gym',        0.55, 1.00, 0.65, 1.00, -12.0,  0.0, 0.00, 0.35, 0.00, 0.45, NULL, NULL, NULL, NULL, 0.35, 1.00, 115.0, 200.0),
  (2, 'study',      0.00, 0.70, 0.00, 0.55, -60.0, -6.0, 0.00, 0.20, 0.35, 1.00, NULL, NULL, NULL, NULL, 0.00, 0.80,  60.0, 130.0),
  (3, 'happy',      0.50, 1.00, 0.45, 1.00, -20.0,  0.0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.60, 1.00,  80.0, 180.0),
  (4, 'sad',        0.00, 0.65, 0.00, 0.50, -60.0, -5.0, NULL, NULL, 0.25, 1.00, NULL, NULL, NULL, NULL, 0.00, 0.40,  50.0, 130.0),
  (5, 'calm',       0.00, 0.70, 0.00, 0.45, -60.0, -7.0, 0.00, 0.25, 0.35, 1.00, NULL, NULL, NULL, NULL, 0.20, 0.80,  50.0, 125.0),
  (6, 'aggressive', 0.35, 1.00, 0.75, 1.00, -10.0,  0.0, NULL, NULL, 0.00, 0.35, NULL, NULL, NULL, NULL, 0.00, 0.75, 100.0, 220.0),
  (7, 'late night', 0.00, 0.75, 0.00, 0.60, -60.0, -5.0, NULL, NULL, 0.15, 1.00, NULL, NULL, NULL, NULL, 0.00, 0.75,  55.0, 135.0);

-- Reset AUTO_INCREMENT values after explicit deterministic IDs.
SET @next_album := (SELECT COALESCE(MAX(AlbumID), 0) + 1 FROM Albums);
SET @next_artist := (SELECT COALESCE(MAX(ArtistID), 0) + 1 FROM Artists);
SET @next_genre := (SELECT COALESCE(MAX(GenreID), 0) + 1 FROM Genres);
SET @next_track := (SELECT COALESCE(MAX(TrackID), 0) + 1 FROM Tracks);
SET @next_mood := (SELECT COALESCE(MAX(MoodProfileID), 0) + 1 FROM MoodProfiles);
SET @next_user := (SELECT COALESCE(MAX(UserID), 0) + 1 FROM Users);

SET @sql := CONCAT('ALTER TABLE Albums AUTO_INCREMENT = ', @next_album); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @sql := CONCAT('ALTER TABLE Artists AUTO_INCREMENT = ', @next_artist); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @sql := CONCAT('ALTER TABLE Genres AUTO_INCREMENT = ', @next_genre); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @sql := CONCAT('ALTER TABLE Tracks AUTO_INCREMENT = ', @next_track); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @sql := CONCAT('ALTER TABLE MoodProfiles AUTO_INCREMENT = ', @next_mood); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @sql := CONCAT('ALTER TABLE Users AUTO_INCREMENT = ', @next_user); PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------------
-- 3) Sanity checks.
-- ---------------------------------------------------------------------------

SELECT 'Rows loaded from CSV staging' AS check_name, COUNT(*) AS row_count FROM stg_spotify_raw
UNION ALL SELECT 'Clean CSV rows used', COUNT(*) FROM stg_spotify_clean
UNION ALL SELECT 'Tracks', COUNT(*) FROM Tracks
UNION ALL SELECT 'AudioFeatures', COUNT(*) FROM AudioFeatures
UNION ALL SELECT 'Albums', COUNT(*) FROM Albums
UNION ALL SELECT 'Artists', COUNT(*) FROM Artists
UNION ALL SELECT 'Genres', COUNT(*) FROM Genres
UNION ALL SELECT 'TrackArtists bridge rows', COUNT(*) FROM TrackArtists
UNION ALL SELECT 'TrackGenres bridge rows', COUNT(*) FROM TrackGenres;

-- Expected for the uploaded dataset, approximately:
--   staging rows:          114000
--   clean rows:            113999  (one row has missing artist/album/track name)
--   Tracks/AudioFeatures:   89740
--   Albums:                 46589
--   Artists:                29858
--   Genres:                   114
--   TrackArtists rows:     123424
--   TrackGenres rows:      113549

-- Drop staging tables when you no longer need to inspect them.
-- DROP TABLE IF EXISTS stg_spotify_raw;
-- DROP TABLE IF EXISTS stg_spotify_clean;
-- DROP TABLE IF EXISTS stg_track_choice;
-- DROP TABLE IF EXISTS stg_artist_split;
-- DROP TABLE IF EXISTS stg_album_map;
-- DROP TABLE IF EXISTS stg_artist_map;
-- DROP TABLE IF EXISTS stg_genre_map;
-- DROP TABLE IF EXISTS stg_track_map;
