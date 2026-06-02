-- ============================================
-- Script to give api permissions.
-- ============================================
USE spotify_explorer;

CREATE USER IF NOT EXISTS 'spotify_api'@'localhost' IDENTIFIED BY 'spotify_password';
ALTER USER 'spotify_api'@'localhost' IDENTIFIED BY 'spotify_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON spotify_explorer.* TO 'spotify_api'@'localhost';
FLUSH PRIVILEGES;
