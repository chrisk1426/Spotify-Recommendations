"""
Python file for analytics endpoints.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/summary', methods=['GET'])
def summary():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM Tracks)  AS TotalTracks,
                (SELECT COUNT(*) FROM Artists) AS TotalArtists,
                (SELECT COUNT(*) FROM Albums)  AS TotalAlbums,
                (SELECT COUNT(*) FROM Genres)  AS TotalGenres,
                AVG(af.Energy)      AS AvgEnergy,
                AVG(af.Valence)     AS AvgValence,
                AVG(af.Tempo)       AS AvgTempo,
                AVG(t.Popularity)   AS AvgPopularity
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID = t.TrackID
        """)
        return jsonify(cursor.fetchone()), 200
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/energetic-genres', methods=['GET'])
def energetic_genres():
    try:
        limit = max(1, int(request.args.get('limit', 20)))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                g.GenreName,
                AVG(af.Energy)  AS AvgEnergy,
                COUNT(t.TrackID) AS TrackCount
            FROM Genres g
            JOIN TrackGenres   tg ON tg.GenreID  = g.GenreID
            JOIN Tracks         t ON  t.TrackID  = tg.TrackID
            JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            GROUP BY g.GenreID, g.GenreName
            HAVING TrackCount >= 10
            ORDER BY AvgEnergy DESC
            LIMIT %s
        """, (limit,))
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/valence-by-genre', methods=['GET'])
def valence_by_genre():
    try:
        limit = max(1, int(request.args.get('limit', 20)))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                g.GenreName,
                AVG(af.Valence)  AS AvgValence,
                COUNT(t.TrackID) AS TrackCount
            FROM Genres g
            JOIN TrackGenres   tg ON tg.GenreID  = g.GenreID
            JOIN Tracks         t ON  t.TrackID  = tg.TrackID
            JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            GROUP BY g.GenreID, g.GenreName
            HAVING TrackCount >= 10
            ORDER BY AvgValence DESC
            LIMIT %s
        """, (limit,))
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/popularity-by-genre', methods=['GET'])
def popularity_by_genre():
    try:
        limit = max(1, int(request.args.get('limit', 20)))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                g.GenreName,
                AVG(t.Popularity) AS AvgPopularity,
                COUNT(t.TrackID)  AS TrackCount
            FROM Genres g
            JOIN TrackGenres tg ON tg.GenreID = g.GenreID
            JOIN Tracks       t ON  t.TrackID = tg.TrackID
            GROUP BY g.GenreID, g.GenreName
            HAVING TrackCount >= 10
            ORDER BY AvgPopularity DESC
            LIMIT %s
        """, (limit,))
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/bpm-distribution', methods=['GET'])
def bpm_distribution():
    # bucket_size controls the width of each BPM bucket (default 10 BPM)
    try:
        bucket_size = max(1, int(request.args.get('bucket_size', 10)))
    except (TypeError, ValueError):
        return jsonify({'error': 'bucket_size must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                bucket.BucketIndex * %s          AS BucketMin,
                bucket.BucketIndex * %s + (%s-1) AS BucketMax,
                COUNT(*)                         AS TrackCount
            FROM (
                SELECT FLOOR(af.Tempo / %s) AS BucketIndex
                FROM AudioFeatures af
                WHERE af.Tempo > 0
            ) AS bucket
            GROUP BY bucket.BucketIndex
            ORDER BY bucket.BucketIndex ASC
        """, (bucket_size, bucket_size, bucket_size, bucket_size))
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/popularity-vs-danceability', methods=['GET'])
def popularity_vs_danceability():
    # Returns a random sample suitable for scatter plotting
    try:
        limit = max(1, min(2000, int(request.args.get('limit', 500))))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                t.TrackID,
                t.TrackName,
                t.Popularity,
                af.Danceability,
                af.Energy,
                af.Valence
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID = t.TrackID
            ORDER BY RAND()
            LIMIT %s
        """, (limit,))
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()
