"""
Python file for playlist endpoints.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

playlists_bp = Blueprint('playlists', __name__)

@playlists_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_playlists(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Playlists WHERE UserID = %s", (user_id,))
        playlists = cursor.fetchall()
        return jsonify(playlists), 200
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/<int:playlist_id>/tracks', methods=['GET'])
def get_playlist_tracks(playlist_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.TrackID, t.TrackName, t.Duration, t.Popularity
            FROM PlaylistTracks pt
            JOIN Tracks t ON t.TrackID = pt.TrackID
            WHERE pt.PlaylistID = %s
        """, (playlist_id,))
        tracks = cursor.fetchall()
        return jsonify(tracks), 200
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/', methods=['POST'])
def create_playlist():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    mood_profile_id = data.get('mood_profile_id')
    track_ids = data.get('track_ids', [])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()

        cursor.execute("""
            INSERT INTO Playlists (PlaylistName, UserID, MoodProfileID, CreatedAt, UpdatedAt)
            VALUES (%s, %s, %s, NOW(), NOW())
        """, (name, user_id, mood_profile_id))
        playlist_id = cursor.lastrowid

        for track_id in track_ids:
            cursor.execute("""
                INSERT IGNORE INTO PlaylistTracks (PlaylistID, TrackID)
                VALUES (%s, %s)
            """, (playlist_id, track_id))

        conn.commit()
        return jsonify({'message': 'Playlist created', 'playlist_id': playlist_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/<int:playlist_id>/tracks', methods=['POST'])
def add_track(playlist_id):
    data = request.get_json()
    track_id = data.get('track_id')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("""
            INSERT IGNORE INTO PlaylistTracks (PlaylistID, TrackID) VALUES (%s, %s)
        """, (playlist_id, track_id))
        cursor.execute("UPDATE Playlists SET UpdatedAt = NOW() WHERE PlaylistID = %s", (playlist_id,))
        conn.commit()
        return jsonify({'message': 'Track added'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/<int:playlist_id>/tracks/<int:track_id>', methods=['DELETE'])
def remove_track(playlist_id, track_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("""
            DELETE FROM PlaylistTracks WHERE PlaylistID = %s AND TrackID = %s
        """, (playlist_id, track_id))
        cursor.execute("UPDATE Playlists SET UpdatedAt = NOW() WHERE PlaylistID = %s", (playlist_id,))
        conn.commit()
        return jsonify({'message': 'Track removed'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/<int:playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("DELETE FROM PlaylistTracks WHERE PlaylistID = %s", (playlist_id,))
        cursor.execute("DELETE FROM Playlists WHERE PlaylistID = %s", (playlist_id,))
        conn.commit()
        return jsonify({'message': 'Playlist deleted'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@playlists_bp.route('/<int:playlist_id>', methods=['PUT'])
def update_playlist(playlist_id):
    data = request.get_json()
    name = data.get('name')
    mood_profile_id = data.get('mood_profile_id')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE Playlists SET PlaylistName = %s, MoodProfileID = %s, UpdatedAt = NOW()
            WHERE PlaylistID = %s
        """, (name, mood_profile_id, playlist_id))
        conn.commit()
        return jsonify({'message': 'Playlist updated'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@playlists_bp.route('/generate', methods=['POST'])
def generate_playlist():
    data = request.get_json()
    user_id = data.get('user_id')
    mood_profile_id = data.get('mood_profile_id')
    name = data.get('name')
    limit = data.get('limit', 20)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM MoodProfiles WHERE MoodProfileID = %s", (mood_profile_id,))
        mood = cursor.fetchone()
        if not mood:
            return jsonify({'error': 'Mood profile not found'}), 404

        cursor.execute("""
            SELECT t.TrackID
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID = t.TrackID
            WHERE
                af.Danceability BETWEEN %s AND %s AND
                af.Energy BETWEEN %s AND %s AND
                af.Loudness BETWEEN %s AND %s AND
                af.Valence BETWEEN %s AND %s AND
                af.Tempo BETWEEN %s AND %s
            ORDER BY t.Popularity DESC
            LIMIT %s
        """, (
            mood['MinDanceability'], mood['MaxDanceability'],
            mood['MinEnergy'], mood['MaxEnergy'],
            mood['MinLoudness'], mood['MaxLoudness'],
            mood['MinValence'], mood['MaxValence'],
            mood['MinTempo'], mood['MaxTempo'],
            limit
        ))
        tracks = cursor.fetchall()
        if not tracks:
            return jsonify({'error': 'No tracks found for this mood profile'}), 404

        cursor.execute("""
            INSERT INTO Playlists (PlaylistName, UserID, MoodProfileID, CreatedAt, UpdatedAt)
            VALUES (%s, %s, %s, NOW(), NOW())
        """, (name, user_id, mood_profile_id))
        playlist_id = cursor.lastrowid

        for track in tracks:
            cursor.execute("""
                INSERT IGNORE INTO PlaylistTracks (PlaylistID, TrackID)
                VALUES (%s, %s)
            """, (playlist_id, track['TrackID']))

        conn.commit()
        return jsonify({'message': 'Playlist generated', 'playlist_id': playlist_id, 'track_count': len(tracks)}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()