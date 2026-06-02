"""
Python file for album endpoints.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

albums_bp = Blueprint('albums', __name__)


@albums_bp.route('/', methods=['GET'])
def get_albums():
    search = request.args.get('q', '')
    try:
        limit = max(1, int(request.args.get('limit', 50)))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if search:
            cursor.execute("""
                SELECT
                    al.AlbumID,
                    al.AlbumName,
                    COUNT(t.TrackID) AS TrackCount
                FROM Albums al
                LEFT JOIN Tracks t ON t.AlbumID = al.AlbumID
                WHERE al.AlbumName LIKE %s
                GROUP BY al.AlbumID, al.AlbumName
                ORDER BY al.AlbumName
                LIMIT %s
            """, (f'%{search}%', limit))
        else:
            cursor.execute("""
                SELECT
                    al.AlbumID,
                    al.AlbumName,
                    COUNT(t.TrackID) AS TrackCount
                FROM Albums al
                LEFT JOIN Tracks t ON t.AlbumID = al.AlbumID
                GROUP BY al.AlbumID, al.AlbumName
                ORDER BY al.AlbumName
                LIMIT %s
            """, (limit,))

        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@albums_bp.route('/<int:album_id>', methods=['GET'])
def get_album(album_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                al.AlbumID,
                al.AlbumName,
                COUNT(t.TrackID)  AS TrackCount,
                AVG(t.Popularity) AS AvgPopularity
            FROM Albums al
            LEFT JOIN Tracks t ON t.AlbumID = al.AlbumID
            WHERE al.AlbumID = %s
            GROUP BY al.AlbumID, al.AlbumName
        """, (album_id,))

        album = cursor.fetchone()
        if not album or album['AlbumName'] is None:
            return jsonify({'error': 'Album not found'}), 404

        return jsonify(album), 200
    finally:
        cursor.close()
        conn.close()


@albums_bp.route('/<int:album_id>/tracks', methods=['GET'])
def get_album_tracks(album_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT AlbumID FROM Albums WHERE AlbumID = %s", (album_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Album not found'}), 404

        cursor.execute("""
            SELECT
                t.TrackID,
                t.SpotifyTrackID,
                t.TrackName,
                t.Duration,
                t.Popularity,
                t.IsExplicit,
                af.Danceability,
                af.Energy,
                af.`Key`              AS SpotifyKey,
                af.Loudness,
                af.`Mode`             AS SpotifyMode,
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
            LEFT JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            LEFT JOIN TrackArtists  ta ON ta.TrackID  = t.TrackID
            LEFT JOIN Artists       ar ON ar.ArtistID = ta.ArtistID
            LEFT JOIN TrackGenres   tg ON tg.TrackID  = t.TrackID
            LEFT JOIN Genres         g ON  g.GenreID  = tg.GenreID
            WHERE t.AlbumID = %s
            GROUP BY
                t.TrackID, t.SpotifyTrackID, t.TrackName, t.Duration,
                t.Popularity, t.IsExplicit,
                af.Danceability, af.Energy, af.`Key`, af.Loudness, af.`Mode`,
                af.Speechiness, af.Acousticness, af.Instrumentalness,
                af.Liveness, af.Valence, af.Tempo, af.TimeSignature
            ORDER BY t.Popularity DESC
        """, (album_id,))

        tracks = cursor.fetchall()
        for row in tracks:
            for field in ('Artists', 'Genres'):
                row[field] = row[field].split(', ') if row.get(field) else []

        return jsonify(tracks), 200
    finally:
        cursor.close()
        conn.close()
