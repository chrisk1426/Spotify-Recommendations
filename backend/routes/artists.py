# Routes/Endpoint/CRUD Operations for the Artists resource
from flask import Blueprint, request, jsonify
from db import get_connection

artists_bp = Blueprint('artists', __name__)


# Validate the limit query 
def parse_limit(raw):
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return None
    if limit < 1:
        return None
    return limit


# list artists with a track count
@artists_bp.route('/', methods=['GET'])
def get_artists():
    search = request.args.get('q', '')

    limit = parse_limit(request.args.get('limit', 50))
    if limit is None:
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # gives each artist their number of tracks 
        if search:
            cursor.execute("""
                SELECT
                    a.ArtistID,
                    a.ArtistName,
                    COUNT(ta.TrackID) AS TrackCount
                FROM Artists a
                LEFT JOIN TrackArtists ta ON ta.ArtistID = a.ArtistID
                WHERE a.ArtistName LIKE %s
                GROUP BY a.ArtistID, a.ArtistName
                ORDER BY a.ArtistName
                LIMIT %s
            """, (f'%{search}%', limit))
        else:
            cursor.execute("""
                SELECT 
                    a.ArtistID,
                    a.ArtistName,
                    COUNT(ta.TrackID) AS TrackCount
                FROM Artists a
                LEFT JOIN TrackArtists ta ON ta.ArtistID = a.ArtistID
                GROUP BY a.ArtistID, a.ArtistName
                ORDER BY a.ArtistName
                LIMIT %s
            """, (limit,))

        artists = cursor.fetchall()
        return jsonify(artists), 200

    finally:
        cursor.close()
        conn.close()


# the artist plus the full list of their tracks.
@artists_bp.route('/<int:artist_id>', methods=['GET'])
def get_artist(artist_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # the artist summary: name + track count
        cursor.execute("""
            SELECT
                a.ArtistID,
                a.ArtistName,
                COUNT(ta.TrackID) AS TrackCount
            FROM Artists a
            LEFT JOIN TrackArtists ta ON ta.ArtistID = a.ArtistID
            WHERE a.ArtistID = %s
            GROUP BY a.ArtistID, a.ArtistName
        """, (artist_id,))

        artist = cursor.fetchone()

        if not artist:
            return jsonify({'error': 'Artist not found'}), 404

        # every track by this artist, with details and the
        # artist/genre names 
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
            WHERE t.TrackID IN (SELECT TrackID FROM TrackArtists WHERE ArtistID = %s)
            GROUP BY
                t.TrackID, t.SpotifyTrackID, t.TrackName, t.Duration,
                t.Popularity, t.IsExplicit, t.AlbumID, al.AlbumName,
                af.Danceability, af.Energy, af.`Key`, af.Loudness, af.`Mode`,
                af.Speechiness, af.Acousticness, af.Instrumentalness,
                af.Liveness, af.Valence, af.Tempo, af.TimeSignature
            ORDER BY t.Popularity DESC
        """, (artist_id,))

        # Split the comma-joined Artists and Genres strings back into JSON arrays.
        tracks = cursor.fetchall()
        for row in tracks:
            for field in ('Artists', 'Genres'):
                row[field] = row[field].split(', ') if row.get(field) else []
        artist['tracks'] = tracks  # attach the track list to the artist object

        return jsonify(artist), 200

    finally:
        cursor.close()
        conn.close()


# create a new artist from an artist_name
@artists_bp.route('/', methods=['POST'])
def create_artist():
    data = request.get_json()
    artist_name = data.get('artist_name')

    if not artist_name:
        return jsonify({'error': 'artist_name is required'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "INSERT INTO Artists (ArtistName) VALUES (%s)",
            (artist_name,)
        )

        conn.commit()
        artist_id = cursor.lastrowid

        return jsonify({
            'message': 'Artist created',
            'ArtistID': artist_id,
            'ArtistName': artist_name
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()


# rename an existing artist.
@artists_bp.route('/<int:artist_id>', methods=['PUT'])
def update_artist(artist_id):
    data = request.get_json()
    artist_name = data.get('artist_name')

    if not artist_name:
        return jsonify({'error': 'artist_name is required'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT ArtistID FROM Artists WHERE ArtistID = %s",
            (artist_id,)
        )

        if not cursor.fetchone():
            return jsonify({'error': 'Artist not found'}), 404

        cursor.execute(
            "UPDATE Artists SET ArtistName = %s WHERE ArtistID = %s",
            (artist_name, artist_id)
        )

        conn.commit()

        return jsonify({
            'message': 'Artist updated',
            'ArtistID': artist_id,
            'ArtistName': artist_name
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()


# delete an artist; refuses if still linked to tracks
@artists_bp.route('/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    force = request.args.get('force', 'false').lower() == 'true'

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check whether the artist is still attached to any tracks.
        cursor.execute(
            "SELECT COUNT(*) AS TrackCount FROM TrackArtists WHERE ArtistID = %s",
            (artist_id,)
        )

        result = cursor.fetchone()

        # Block the delete unless the caller explicitly forces it.
        if result['TrackCount'] > 0 and not force:
            return jsonify({
                'error': 'Artist is linked to tracks. Use ?force=true to remove the artist-track links first.'
            }), 409

        if force:
            cursor.execute(
                "DELETE FROM TrackArtists WHERE ArtistID = %s",
                (artist_id,)
            )

        cursor.execute(
            "DELETE FROM Artists WHERE ArtistID = %s",
            (artist_id,)
        )

        # rowcount 0 means no such artist existed to delete.
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({'error': 'Artist not found'}), 404

        conn.commit()

        return jsonify({
            'message': 'Artist deleted',
            'ArtistID': artist_id
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()
        conn.close()