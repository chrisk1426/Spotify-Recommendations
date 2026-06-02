/*
  add_indexes_constraints.sql
  ---------------------------
  Run once against spotify_explorer AFTER load_spotify_3nf.sql has been executed.
  Safe to re-run: indexes and constraints use INFORMATION_SCHEMA guards.

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

DROP PROCEDURE IF EXISTS add_index_if_missing;

DELIMITER //
CREATE PROCEDURE add_index_if_missing(
  IN table_name_in VARCHAR(64),
  IN index_name_in VARCHAR(64),
  IN ddl_in TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_in
      AND INDEX_NAME = index_name_in
  ) THEN
    SET @index_sql := ddl_in;
    PREPARE index_stmt FROM @index_sql;
    EXECUTE index_stmt;
    DEALLOCATE PREPARE index_stmt;
  ELSE
    SELECT CONCAT(index_name_in, ' already exists') AS info;
  END IF;
END//
DELIMITER ;

-- Tracks.Popularity DESC — used in ORDER BY across almost every route
CALL add_index_if_missing('Tracks', 'idx_tracks_popularity',
  'ALTER TABLE Tracks ADD INDEX idx_tracks_popularity (Popularity DESC)');

-- Tracks.AlbumID — FK join in every full-detail track query
CALL add_index_if_missing('Tracks', 'idx_tracks_albumid',
  'ALTER TABLE Tracks ADD INDEX idx_tracks_albumid (AlbumID)');

-- Playlists.UserID — WHERE UserID = ? in GET /playlists/user/<id>
CALL add_index_if_missing('Playlists', 'idx_playlists_userid',
  'ALTER TABLE Playlists ADD INDEX idx_playlists_userid (UserID)');

-- Playlists.MoodProfileID — FK join for mood-based playlist queries
CALL add_index_if_missing('Playlists', 'idx_playlists_moodprofileid',
  'ALTER TABLE Playlists ADD INDEX idx_playlists_moodprofileid (MoodProfileID)');

-- TrackArtists.ArtistID — reverse lookup: all tracks by an artist
CALL add_index_if_missing('TrackArtists', 'idx_trackartists_artistid',
  'ALTER TABLE TrackArtists ADD INDEX idx_trackartists_artistid (ArtistID)');

-- TrackGenres.GenreID — reverse lookup: all tracks in a genre
CALL add_index_if_missing('TrackGenres', 'idx_trackgenres_genreid',
  'ALTER TABLE TrackGenres ADD INDEX idx_trackgenres_genreid (GenreID)');

-- RecommendationHistory — fetch history by user, by track, by date
CALL add_index_if_missing('RecommendationHistory', 'idx_rechistory_userid',
  'ALTER TABLE RecommendationHistory ADD INDEX idx_rechistory_userid (UserID)');
CALL add_index_if_missing('RecommendationHistory', 'idx_rechistory_trackid',
  'ALTER TABLE RecommendationHistory ADD INDEX idx_rechistory_trackid (TrackID)');
CALL add_index_if_missing('RecommendationHistory', 'idx_rechistory_generatedat',
  'ALTER TABLE RecommendationHistory ADD INDEX idx_rechistory_generatedat (GeneratedAt DESC)');

-- AudioFeatures individual columns — single-column analytics queries
CALL add_index_if_missing('AudioFeatures', 'idx_af_energy',
  'ALTER TABLE AudioFeatures ADD INDEX idx_af_energy (Energy)');
CALL add_index_if_missing('AudioFeatures', 'idx_af_danceability',
  'ALTER TABLE AudioFeatures ADD INDEX idx_af_danceability (Danceability)');
CALL add_index_if_missing('AudioFeatures', 'idx_af_valence',
  'ALTER TABLE AudioFeatures ADD INDEX idx_af_valence (Valence)');
CALL add_index_if_missing('AudioFeatures', 'idx_af_tempo',
  'ALTER TABLE AudioFeatures ADD INDEX idx_af_tempo (Tempo)');

-- ===========================================================================
-- 4. COMPOSITE INDEX for mood / generate-playlist range filtering
--    Covers the multi-column BETWEEN filters in mood search and playlist generation.
--    MySQL uses the leftmost prefix, so Energy must be the most selective
--    leading column for typical mood queries.
-- ===========================================================================

CALL add_index_if_missing('AudioFeatures', 'idx_af_mood_composite',
  'ALTER TABLE AudioFeatures ADD INDEX idx_af_mood_composite (Energy, Danceability, Valence, Tempo)');

DROP PROCEDURE IF EXISTS add_index_if_missing;

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
GROUP BY TABLE_NAME, INDEX_NAME
ORDER BY TABLE_NAME, INDEX_NAME;
