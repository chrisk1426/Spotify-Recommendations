"""
Python file containing endpoint for genres.
"""
from flask import Blueprint, request, jsonify
from db import get_connection

genres_bp = Blueprint('genres', __name__)


@genres_bp.route('/', methods=['GET'])
def get_all_genres():
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
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.TrackID, t.TrackName, t.Duration, t.Popularity
            FROM Tracks t
            JOIN TrackGenres tg ON tg.TrackID = t.TrackID
            WHERE tg.GenreID = %s
            ORDER BY t.Popularity DESC
        """, (genre_id,))
        tracks = cursor.fetchall()
        if not tracks:
            return jsonify({'error': 'No tracks found for this genre'}), 404
        return jsonify(tracks), 200
    finally:
        cursor.close()
        conn.close()