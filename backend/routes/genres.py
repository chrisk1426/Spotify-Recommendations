"""
Python file containing API endpoints for genre table.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

genres_bp = Blueprint('genres', __name__)


@genres_bp.route('/', methods=['GET'])
def get_all_genres():
    """
    Endpoint to retrieve all music genres available.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Genres ORDER BY GenreName")
        genres = cursor.fetchall()
        return jsonify(genres), 200
    finally:
        cursor.close()
        conn.close()


@genres_bp.route('/<int:genre_id>/tracks', methods=['GET'])
def get_tracks_by_genre(genre_id):
    """
    Endpoint to retrieve tracks by genre.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                t.TrackID,
                t.SpotifyTrackID,
                t.TrackName,
                t.Duration,
                t.Popularity,
                t.IsExplicit,
                t.AlbumID,
                al.AlbumName,
                af.Danceability,
                af.Energy,
                af.`Key`             AS SpotifyKey,
                af.Loudness,
                af.`Mode`            AS SpotifyMode,
                af.Speechiness,
                af.Acousticness,
                af.Instrumentalness,
                af.Liveness,
                af.Valence,
                af.Tempo,
                af.TimeSignature,
                GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                GROUP_CONCAT(DISTINCT g.GenreName   ORDER BY g.GenreName   SEPARATOR ', ') AS Genres
            FROM Tracks t
            LEFT JOIN Albums al        ON al.AlbumID  = t.AlbumID
            LEFT JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            LEFT JOIN TrackArtists  ta ON ta.TrackID  = t.TrackID
            LEFT JOIN Artists       ar ON ar.ArtistID = ta.ArtistID
            LEFT JOIN TrackGenres   tg ON tg.TrackID  = t.TrackID
            LEFT JOIN Genres         g ON  g.GenreID  = tg.GenreID
            WHERE t.TrackID IN (SELECT TrackID FROM TrackGenres WHERE GenreID = %s)
            GROUP BY
                t.TrackID, t.SpotifyTrackID, t.TrackName, t.Duration,
                t.Popularity, t.IsExplicit, t.AlbumID, al.AlbumName,
                af.Danceability, af.Energy, af.`Key`, af.Loudness, af.`Mode`,
                af.Speechiness, af.Acousticness, af.Instrumentalness,
                af.Liveness, af.Valence, af.Tempo, af.TimeSignature
            ORDER BY t.Popularity DESC
        """, (genre_id,))
        tracks = cursor.fetchall()
        if not tracks:
            return jsonify({'error': 'No tracks found for this genre'}), 404
        for row in tracks:
            for field in ('Artists', 'Genres'):
                row[field] = row[field].split(', ') if row.get(field) else []
        return jsonify(tracks), 200
    finally:
        cursor.close()
        conn.close()