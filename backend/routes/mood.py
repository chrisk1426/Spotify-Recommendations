"""
Python file for mood search endpoints.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

mood_bp = Blueprint('mood', __name__)

# AudioFeatures columns that a MoodProfile can constrain, mapped to their DB column names.
MOOD_FEATURE_COLUMNS = [
    ('MinDanceability',      'MaxDanceability',      'af.Danceability'),
    ('MinEnergy',            'MaxEnergy',            'af.Energy'),
    ('MinLoudness',          'MaxLoudness',          'af.Loudness'),
    ('MinSpeechiness',       'MaxSpeechiness',       'af.Speechiness'),
    ('MinAcousticness',      'MaxAcousticness',      'af.Acousticness'),
    ('MinInstrumentalness',  'MaxInstrumentalness',  'af.Instrumentalness'),
    ('MinLiveness',          'MaxLiveness',          'af.Liveness'),
    ('MinValence',           'MaxValence',           'af.Valence'),
    ('MinTempo',             'MaxTempo',             'af.Tempo'),
]


def _build_mood_where(mood):
    """
    Build WHERE clause fragments for non-NULL min/max pairs in a mood profile row.
    Returns (clauses, params) where clauses is a list of SQL strings and
    params is a flat list of values to bind.
    """
    clauses = []
    params = []
    for min_col, max_col, af_col in MOOD_FEATURE_COLUMNS:
        lo = mood.get(min_col)
        hi = mood.get(max_col)
        if lo is not None and hi is not None:
            clauses.append(f"{af_col} BETWEEN %s AND %s")
            params.extend([lo, hi])
        elif lo is not None:
            clauses.append(f"{af_col} >= %s")
            params.append(lo)
        elif hi is not None:
            clauses.append(f"{af_col} <= %s")
            params.append(hi)
    return clauses, params


@mood_bp.route('/profiles', methods=['GET'])
def get_profiles():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM MoodProfiles ORDER BY MoodProfileName")
        return jsonify(cursor.fetchall()), 200
    finally:
        cursor.close()
        conn.close()


@mood_bp.route('/profiles/<int:mood_profile_id>', methods=['GET'])
def get_profile(mood_profile_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM MoodProfiles WHERE MoodProfileID = %s",
            (mood_profile_id,)
        )
        profile = cursor.fetchone()
        if not profile:
            return jsonify({'error': 'Mood profile not found'}), 404
        return jsonify(profile), 200
    finally:
        cursor.close()
        conn.close()


@mood_bp.route('/search', methods=['GET'])
def mood_search():
    mood_name = request.args.get('mood', '').strip().lower()
    if not mood_name:
        return jsonify({'error': 'mood query parameter is required'}), 400

    try:
        limit = max(1, min(200, int(request.args.get('limit', 50))))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM MoodProfiles WHERE LOWER(MoodProfileName) = %s",
            (mood_name,)
        )
        mood = cursor.fetchone()
        if not mood:
            return jsonify({'error': f"No mood profile found for '{mood_name}'"}), 404

        clauses, params = _build_mood_where(mood)

        where_sql = ''
        if clauses:
            where_sql = 'WHERE ' + ' AND '.join(clauses)

        params.append(limit)

        cursor.execute(f"""
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
                af.Loudness,
                af.Speechiness,
                af.Acousticness,
                af.Instrumentalness,
                af.Liveness,
                af.Valence,
                af.Tempo,
                GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                GROUP_CONCAT(DISTINCT g.GenreName   ORDER BY g.GenreName   SEPARATOR ', ') AS Genres
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            LEFT JOIN Albums        al ON al.AlbumID  = t.AlbumID
            LEFT JOIN TrackArtists  ta ON ta.TrackID  = t.TrackID
            LEFT JOIN Artists       ar ON ar.ArtistID = ta.ArtistID
            LEFT JOIN TrackGenres   tg ON tg.TrackID  = t.TrackID
            LEFT JOIN Genres         g ON  g.GenreID  = tg.GenreID
            {where_sql}
            GROUP BY
                t.TrackID, t.SpotifyTrackID, t.TrackName, t.Duration,
                t.Popularity, t.IsExplicit, t.AlbumID, al.AlbumName,
                af.Danceability, af.Energy, af.Loudness, af.Speechiness,
                af.Acousticness, af.Instrumentalness, af.Liveness, af.Valence, af.Tempo
            ORDER BY t.Popularity DESC
            LIMIT %s
        """, params)

        tracks = cursor.fetchall()
        for row in tracks:
            for field in ('Artists', 'Genres'):
                row[field] = row[field].split(', ') if row.get(field) else []

        return jsonify({
            'mood_profile': {
                'id':   mood['MoodProfileID'],
                'name': mood['MoodProfileName'],
            },
            'track_count': len(tracks),
            'tracks': tracks,
        }), 200

    finally:
        cursor.close()
        conn.close()
