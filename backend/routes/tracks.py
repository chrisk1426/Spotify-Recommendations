from flask import Blueprint, request, jsonify
from db import get_connection

tracks_bp = Blueprint('tracks', __name__)


def bool_to_int(value):
    if value in [True, 1, '1', 'true', 'True', 'yes', 'Yes']:
        return 1
    return 0


def parse_limit(raw):
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return None
    if limit < 1:
        return None
    return limit


def listify(row):
    """Turn the comma-joined Artists/Genres columns into JSON arrays."""
    if row is None:
        return row
    for field in ('Artists', 'Genres'):
        if field in row:
            row[field] = row[field].split(', ') if row[field] else []
    return row


def get_track_by_id(track_id):
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
                af.`Key` AS SpotifyKey,
                af.Loudness,
                af.`Mode` AS SpotifyMode,
                af.Speechiness,
                af.Acousticness,
                af.Instrumentalness,
                af.Liveness,
                af.Valence,
                af.Tempo,
                af.TimeSignature,
                GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') AS Genres
            FROM Tracks t
            LEFT JOIN Albums al ON al.AlbumID = t.AlbumID
            LEFT JOIN AudioFeatures af ON af.TrackID = t.TrackID
            LEFT JOIN TrackArtists ta ON ta.TrackID = t.TrackID
            LEFT JOIN Artists ar ON ar.ArtistID = ta.ArtistID
            LEFT JOIN TrackGenres tg ON tg.TrackID = t.TrackID
            LEFT JOIN Genres g ON g.GenreID = tg.GenreID
            WHERE t.TrackID = %s
            GROUP BY 
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
                af.`Key`,
                af.Loudness,
                af.`Mode`,
                af.Speechiness,
                af.Acousticness,
                af.Instrumentalness,
                af.Liveness,
                af.Valence,
                af.Tempo,
                af.TimeSignature
        """, (track_id,))

        return listify(cursor.fetchone())

    finally:
        cursor.close()
        conn.close()


@tracks_bp.route('/', methods=['GET'])
def get_tracks():
    search = request.args.get('q', '')

    limit = parse_limit(request.args.get('limit', 50))
    if limit is None:
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if search:
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
                    af.Energy,
                    af.Tempo,
                    af.Valence,
                    GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                    GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') AS Genres
                FROM Tracks t
                LEFT JOIN Albums al ON al.AlbumID = t.AlbumID
                LEFT JOIN AudioFeatures af ON af.TrackID = t.TrackID
                LEFT JOIN TrackArtists ta ON ta.TrackID = t.TrackID
                LEFT JOIN Artists ar ON ar.ArtistID = ta.ArtistID
                LEFT JOIN TrackGenres tg ON tg.TrackID = t.TrackID
                LEFT JOIN Genres g ON g.GenreID = tg.GenreID
                WHERE t.TrackID IN (
                    SELECT t2.TrackID
                    FROM Tracks t2
                    LEFT JOIN Albums al2 ON al2.AlbumID = t2.AlbumID
                    LEFT JOIN TrackArtists ta2 ON ta2.TrackID = t2.TrackID
                    LEFT JOIN Artists ar2 ON ar2.ArtistID = ta2.ArtistID
                    LEFT JOIN TrackGenres tg2 ON tg2.TrackID = t2.TrackID
                    LEFT JOIN Genres g2 ON g2.GenreID = tg2.GenreID
                    WHERE
                        t2.TrackName LIKE %s
                        OR al2.AlbumName LIKE %s
                        OR ar2.ArtistName LIKE %s
                        OR g2.GenreName LIKE %s
                )
                GROUP BY
                    t.TrackID,
                    t.SpotifyTrackID,
                    t.TrackName,
                    t.Duration,
                    t.Popularity,
                    t.IsExplicit,
                    t.AlbumID,
                    al.AlbumName,
                    af.Energy,
                    af.Tempo,
                    af.Valence
                ORDER BY t.Popularity DESC
                LIMIT %s
            """, (
                f'%{search}%',
                f'%{search}%',
                f'%{search}%',
                f'%{search}%',
                limit
            ))
        else:
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
                    af.Energy,
                    af.Tempo,
                    af.Valence,
                    GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                    GROUP_CONCAT(DISTINCT g.GenreName ORDER BY g.GenreName SEPARATOR ', ') AS Genres
                FROM Tracks t
                LEFT JOIN Albums al ON al.AlbumID = t.AlbumID
                LEFT JOIN AudioFeatures af ON af.TrackID = t.TrackID
                LEFT JOIN TrackArtists ta ON ta.TrackID = t.TrackID
                LEFT JOIN Artists ar ON ar.ArtistID = ta.ArtistID
                LEFT JOIN TrackGenres tg ON tg.TrackID = t.TrackID
                LEFT JOIN Genres g ON g.GenreID = tg.GenreID
                GROUP BY
                    t.TrackID,
                    t.SpotifyTrackID,
                    t.TrackName,
                    t.Duration,
                    t.Popularity,
                    t.IsExplicit,
                    t.AlbumID,
                    al.AlbumName,
                    af.Energy,
                    af.Tempo,
                    af.Valence
                ORDER BY t.Popularity DESC
                LIMIT %s
            """, (limit,))

        tracks = [listify(t) for t in cursor.fetchall()]
        return jsonify(tracks), 200

    finally:
        cursor.close()
        conn.close()


@tracks_bp.route('/<int:track_id>', methods=['GET'])
def get_track(track_id):
    track = get_track_by_id(track_id)

    if not track:
        return jsonify({'error': 'Track not found'}), 404

    return jsonify(track), 200


@tracks_bp.route('/', methods=['POST'])
def create_track():
    data = request.get_json()

    track_name = data.get('track_name')
    spotify_track_id = data.get('spotify_track_id')
    duration = data.get('duration')
    popularity = data.get('popularity')
    is_explicit = bool_to_int(data.get('is_explicit', False))
    album_id = data.get('album_id')

    artist_ids = data.get('artist_ids', [])
    genre_ids = data.get('genre_ids', [])
    audio = data.get('audio_features', {})

    if not track_name:
        return jsonify({'error': 'track_name is required'}), 400

    if not album_id:
        return jsonify({'error': 'album_id is required'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO Tracks
                (SpotifyTrackID, TrackName, Duration, Popularity, IsExplicit, AlbumID)
            VALUES 
                (%s, %s, %s, %s, %s, %s)
        """, (
            spotify_track_id,
            track_name,
            duration,
            popularity,
            is_explicit,
            album_id
        ))

        track_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO AudioFeatures
                (TrackID, Danceability, Energy, `Key`, Loudness, `Mode`, Speechiness,
                 Acousticness, Instrumentalness, Liveness, Valence, Tempo, TimeSignature)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            track_id,
            audio.get('danceability'),
            audio.get('energy'),
            audio.get('key'),
            audio.get('loudness'),
            audio.get('mode'),
            audio.get('speechiness'),
            audio.get('acousticness'),
            audio.get('instrumentalness'),
            audio.get('liveness'),
            audio.get('valence'),
            audio.get('tempo'),
            audio.get('time_signature')
        ))

        for artist_id in artist_ids:
            cursor.execute("""
                INSERT INTO TrackArtists (TrackID, ArtistID)
                VALUES (%s, %s)
            """, (track_id, artist_id))

        for genre_id in genre_ids:
            cursor.execute("""
                INSERT INTO TrackGenres (TrackID, GenreID)
                VALUES (%s, %s)
            """, (track_id, genre_id))

        conn.commit()

        new_track = get_track_by_id(track_id)

        return jsonify({
            'message': 'Track created',
            'track': new_track
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()


@tracks_bp.route('/<int:track_id>', methods=['PUT'])
def update_track(track_id):
    data = request.get_json()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT TrackID FROM Tracks WHERE TrackID = %s",
            (track_id,)
        )

        if not cursor.fetchone():
            return jsonify({'error': 'Track not found'}), 404

        track_updates = []
        track_values = []

        if 'spotify_track_id' in data:
            track_updates.append("SpotifyTrackID = %s")
            track_values.append(data.get('spotify_track_id'))

        if 'track_name' in data:
            track_updates.append("TrackName = %s")
            track_values.append(data.get('track_name'))

        if 'duration' in data:
            track_updates.append("Duration = %s")
            track_values.append(data.get('duration'))

        if 'popularity' in data:
            track_updates.append("Popularity = %s")
            track_values.append(data.get('popularity'))

        if 'is_explicit' in data:
            track_updates.append("IsExplicit = %s")
            track_values.append(bool_to_int(data.get('is_explicit')))

        if 'album_id' in data:
            track_updates.append("AlbumID = %s")
            track_values.append(data.get('album_id'))

        if track_updates:
            track_values.append(track_id)

            cursor.execute(f"""
                UPDATE Tracks
                SET {', '.join(track_updates)}
                WHERE TrackID = %s
            """, tuple(track_values))

        if 'audio_features' in data:
            audio = data.get('audio_features', {})

            audio_updates = []
            audio_values = []

            audio_fields = {
                'danceability': 'Danceability',
                'energy': 'Energy',
                'key': '`Key`',
                'loudness': 'Loudness',
                'mode': '`Mode`',
                'speechiness': 'Speechiness',
                'acousticness': 'Acousticness',
                'instrumentalness': 'Instrumentalness',
                'liveness': 'Liveness',
                'valence': 'Valence',
                'tempo': 'Tempo',
                'time_signature': 'TimeSignature'
            }

            for json_field, db_column in audio_fields.items():
                if json_field in audio:
                    audio_updates.append(f"{db_column} = %s")
                    audio_values.append(audio.get(json_field))

            if audio_updates:
                audio_values.append(track_id)

                cursor.execute(f"""
                    UPDATE AudioFeatures
                    SET {', '.join(audio_updates)}
                    WHERE TrackID = %s
                """, tuple(audio_values))

        if 'artist_ids' in data:
            cursor.execute(
                "DELETE FROM TrackArtists WHERE TrackID = %s",
                (track_id,)
            )

            for artist_id in data.get('artist_ids', []):
                cursor.execute("""
                    INSERT INTO TrackArtists (TrackID, ArtistID)
                    VALUES (%s, %s)
                """, (track_id, artist_id))

        if 'genre_ids' in data:
            cursor.execute(
                "DELETE FROM TrackGenres WHERE TrackID = %s",
                (track_id,)
            )

            for genre_id in data.get('genre_ids', []):
                cursor.execute("""
                    INSERT INTO TrackGenres (TrackID, GenreID)
                    VALUES (%s, %s)
                """, (track_id, genre_id))

        conn.commit()

        updated_track = get_track_by_id(track_id)

        return jsonify({
            'message': 'Track updated',
            'track': updated_track
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()


@tracks_bp.route('/<int:track_id>', methods=['DELETE'])
def delete_track(track_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT TrackID FROM Tracks WHERE TrackID = %s",
            (track_id,)
        )

        if not cursor.fetchone():
            return jsonify({'error': 'Track not found'}), 404

        cursor.execute(
            "DELETE FROM RecommendationHistory WHERE TrackID = %s",
            (track_id,)
        )

        cursor.execute(
            "DELETE FROM PlaylistTracks WHERE TrackID = %s",
            (track_id,)
        )

        cursor.execute(
            "DELETE FROM TrackArtists WHERE TrackID = %s",
            (track_id,)
        )

        cursor.execute(
            "DELETE FROM TrackGenres WHERE TrackID = %s",
            (track_id,)
        )

        cursor.execute(
            "DELETE FROM AudioFeatures WHERE TrackID = %s",
            (track_id,)
        )

        cursor.execute(
            "DELETE FROM Tracks WHERE TrackID = %s",
            (track_id,)
        )

        conn.commit()

        return jsonify({
            'message': 'Track deleted',
            'TrackID': track_id
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()