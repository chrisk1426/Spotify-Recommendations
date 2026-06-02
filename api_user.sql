-- ============================================
-- Script to give api permissions.
-- ============================================
USE spotify_explorer;

CREATE USER 'spotify_api'@'localhost' IDENTIFIED BY 'spotify_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON spotify_explorer.* TO 'spotify_api'@'localhost';