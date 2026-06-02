/*
  add_indexes_constraints.sql
  ---------------------------
  Run once against spotify_explorer AFTER load_spotify_3nf.sql has been executed.
  Safe to re-run: indexes use IF NOT EXISTS (MySQL 8.0+), constraints use
  INFORMATION_SCHEMA guards.

  Sections:
    1. Unique constraints
    2. Check constraints
    3. Performance indexes (individual)
    4. Composite index for mood / audio-feature range filtering
*/

USE spotify_explorer;

-- ===========================================================================
-- 1. UNIQUE CONSTRAINTS
-- ===========================================================================

-- Users.UserName must be unique (nothing in the schema enforces this today)
SET @schema := DATABASE();

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE Users ADD CONSTRAINT uq_users_username UNIQUE (UserName)',
    'SELECT ''uq_users_username already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'Users'
    AND CONSTRAINT_NAME = 'uq_users_username'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- MoodProfiles.MoodProfileName must be unique
SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE MoodProfiles ADD CONSTRAINT uq_moodprofiles_name UNIQUE (MoodProfileName)',
    'SELECT ''uq_moodprofiles_name already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'MoodProfiles'
    AND CONSTRAINT_NAME = 'uq_moodprofiles_name'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ===========================================================================
-- 2. CHECK CONSTRAINTS
-- ===========================================================================

-- Tracks.Popularity must be 0–100
SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE Tracks ADD CONSTRAINT chk_tracks_popularity CHECK (Popularity BETWEEN 0 AND 100)',
    'SELECT ''chk_tracks_popularity already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'Tracks'
    AND CONSTRAINT_NAME = 'chk_tracks_popularity'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Users.IsAdmin must be 0 or 1
SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE Users ADD CONSTRAINT chk_users_isadmin CHECK (IsAdmin IN (0, 1))',
    'SELECT ''chk_users_isadmin already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'Users'
    AND CONSTRAINT_NAME = 'chk_users_isadmin'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- AudioFeatures: all 0–1 float columns
SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_danceability CHECK (Danceability BETWEEN 0 AND 1)',
    'SELECT ''chk_af_danceability already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_danceability'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_energy CHECK (Energy BETWEEN 0 AND 1)',
    'SELECT ''chk_af_energy already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_energy'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_speechiness CHECK (Speechiness BETWEEN 0 AND 1)',
    'SELECT ''chk_af_speechiness already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_speechiness'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_acousticness CHECK (Acousticness BETWEEN 0 AND 1)',
    'SELECT ''chk_af_acousticness already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_acousticness'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_instrumentalness CHECK (Instrumentalness BETWEEN 0 AND 1)',
    'SELECT ''chk_af_instrumentalness already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_instrumentalness'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_liveness CHECK (Liveness BETWEEN 0 AND 1)',
    'SELECT ''chk_af_liveness already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_liveness'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_valence CHECK (Valence BETWEEN 0 AND 1)',
    'SELECT ''chk_af_valence already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_valence'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE AudioFeatures ADD CONSTRAINT chk_af_tempo CHECK (Tempo >= 0)',
    'SELECT ''chk_af_tempo already exists'' AS info'
  )
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = @schema
    AND TABLE_NAME   = 'AudioFeatures'
    AND CONSTRAINT_NAME = 'chk_af_tempo'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ===========================================================================
-- 3. PERFORMANCE INDEXES (individual columns)
-- ===========================================================================

-- Tracks.Popularity DESC — used in ORDER BY across almost every route
ALTER TABLE Tracks ADD INDEX IF NOT EXISTS idx_tracks_popularity (Popularity DESC);

-- Tracks.AlbumID — FK join in every full-detail track query
ALTER TABLE Tracks ADD INDEX IF NOT EXISTS idx_tracks_albumid (AlbumID);

-- Playlists.UserID — WHERE UserID = ? in GET /playlists/user/<id>
ALTER TABLE Playlists ADD INDEX IF NOT EXISTS idx_playlists_userid (UserID);

-- Playlists.MoodProfileID — FK join for mood-based playlist queries
ALTER TABLE Playlists ADD INDEX IF NOT EXISTS idx_playlists_moodprofileid (MoodProfileID);

-- TrackArtists.ArtistID — reverse lookup: all tracks by an artist
ALTER TABLE TrackArtists ADD INDEX IF NOT EXISTS idx_trackartists_artistid (ArtistID);

-- TrackGenres.GenreID — reverse lookup: all tracks in a genre
ALTER TABLE TrackGenres ADD INDEX IF NOT EXISTS idx_trackgenres_genreid (GenreID);

-- RecommendationHistory — fetch history by user, by track, by date
ALTER TABLE RecommendationHistory ADD INDEX IF NOT EXISTS idx_rechistory_userid (UserID);
ALTER TABLE RecommendationHistory ADD INDEX IF NOT EXISTS idx_rechistory_trackid (TrackID);
ALTER TABLE RecommendationHistory ADD INDEX IF NOT EXISTS idx_rechistory_generatedat (GeneratedAt DESC);

-- AudioFeatures individual columns — single-column analytics queries
ALTER TABLE AudioFeatures ADD INDEX IF NOT EXISTS idx_af_energy       (Energy);
ALTER TABLE AudioFeatures ADD INDEX IF NOT EXISTS idx_af_danceability (Danceability);
ALTER TABLE AudioFeatures ADD INDEX IF NOT EXISTS idx_af_valence      (Valence);
ALTER TABLE AudioFeatures ADD INDEX IF NOT EXISTS idx_af_tempo        (Tempo);

-- ===========================================================================
-- 4. COMPOSITE INDEX for mood / generate-playlist range filtering
--    Covers the multi-column BETWEEN filters in mood search and playlist generation.
--    MySQL uses the leftmost prefix, so Energy must be the most selective
--    leading column for typical mood queries.
-- ===========================================================================

ALTER TABLE AudioFeatures
  ADD INDEX IF NOT EXISTS idx_af_mood_composite (Energy, Danceability, Valence, Tempo);

-- ===========================================================================
-- Verification
-- ===========================================================================

SELECT
  TABLE_NAME,
  CONSTRAINT_NAME,
  CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('Tracks', 'Users', 'AudioFeatures', 'MoodProfiles')
  AND CONSTRAINT_TYPE IN ('UNIQUE', 'CHECK')
ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME;

SELECT
  TABLE_NAME,
  INDEX_NAME,
  GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS Columns
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND INDEX_NAME LIKE 'idx_%'
ORDER BY TABLE_NAME, INDEX_NAME;
