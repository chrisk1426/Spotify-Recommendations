"""
Python file for recommendation endpoints.

Scoring formula (all terms produce values in [0, 1]):
  audio_sim = 0.25*(1-|E_s-E_c|) + 0.20*(1-|D_s-D_c|) + 0.20*(1-|V_s-V_c|)
            + 0.15*(1-|A_s-A_c|) + 0.10*(1-|T_s/250 - T_c/250|)
  genre_sim = shared_genres / seed_genre_count   (0 if seed has no genres)
  raw_score = audio_sim*0.90 + genre_sim*0.10
  final     = raw_score * (0.70 + 0.30 * Popularity/100)

The popularity multiplier (floor 0.70) keeps audio similarity dominant while
still surfacing more popular tracks when scores are close.
"""
from flask import Blueprint, request, jsonify
from db import get_connection
from utils import is_admin

recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('/<int:track_id>', methods=['GET'])
def get_recommendations(track_id):
    try:
        limit = max(1, min(50, int(request.args.get('limit', 10))))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    user_id = request.args.get('user_id')
    if user_id is not None:
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'error': 'user_id must be an integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify seed track exists and fetch its audio features
        cursor.execute("""
            SELECT t.TrackID, t.TrackName, af.Energy, af.Danceability, af.Valence,
                   af.Acousticness, af.Tempo
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID = t.TrackID
            WHERE t.TrackID = %s
        """, (track_id,))
        seed = cursor.fetchone()
        if not seed:
            return jsonify({'error': 'Track not found'}), 404

        # Count seed's genres for the overlap denominator
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM TrackGenres WHERE TrackID = %s",
            (track_id,)
        )
        seed_genre_count = cursor.fetchone()['cnt']

        # Build the scoring query.
        # Genre overlap subquery counts how many of the candidate's genres
        # match any of the seed's genres.
        # Tempo is normalised to [0,1] by dividing by 250 before differencing.
        cursor.execute("""
            SELECT
                t.TrackID,
                t.SpotifyTrackID,
                t.TrackName,
                t.Popularity,
                al.AlbumName,
                af.Energy,
                af.Danceability,
                af.Valence,
                af.Acousticness,
                af.Tempo,
                GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists,
                GROUP_CONCAT(DISTINCT g.GenreName   ORDER BY g.GenreName   SEPARATOR ', ') AS Genres,
                -- audio similarity (weights sum to 0.90)
                (
                    0.25 * (1 - ABS(%s - af.Energy))                  +
                    0.20 * (1 - ABS(%s - af.Danceability))            +
                    0.20 * (1 - ABS(%s - af.Valence))                 +
                    0.15 * (1 - ABS(%s - af.Acousticness))            +
                    0.10 * (1 - ABS(%s / 250 - af.Tempo / 250))
                ) * 0.90
                -- genre overlap term (weight 0.10)
                + IF(%s > 0,
                    0.10 * (
                        SELECT COUNT(*)
                        FROM TrackGenres cg
                        WHERE cg.TrackID = t.TrackID
                          AND cg.GenreID IN (
                              SELECT GenreID FROM TrackGenres WHERE TrackID = %s
                          )
                    ) / %s,
                    0
                )
                -- popularity multiplier: floor 0.70, ceiling 1.00
                * (0.70 + 0.30 * t.Popularity / 100)
                AS SimilarityScore
            FROM Tracks t
            JOIN AudioFeatures af ON af.TrackID  = t.TrackID
            LEFT JOIN Albums        al ON al.AlbumID  = t.AlbumID
            LEFT JOIN TrackArtists  ta ON ta.TrackID  = t.TrackID
            LEFT JOIN Artists       ar ON ar.ArtistID = ta.ArtistID
            LEFT JOIN TrackGenres   tg ON tg.TrackID  = t.TrackID
            LEFT JOIN Genres         g ON  g.GenreID  = tg.GenreID
            WHERE t.TrackID != %s
            GROUP BY
                t.TrackID, t.SpotifyTrackID, t.TrackName, t.Popularity,
                al.AlbumName,
                af.Energy, af.Danceability, af.Valence, af.Acousticness, af.Tempo
            ORDER BY SimilarityScore DESC
            LIMIT %s
        """, (
            seed['Energy'],
            seed['Danceability'],
            seed['Valence'],
            seed['Acousticness'],
            seed['Tempo'],
            seed_genre_count,
            track_id,
            seed_genre_count if seed_genre_count > 0 else 1,
            track_id,
            limit,
        ))

        results = cursor.fetchall()
        for row in results:
            for field in ('Artists', 'Genres'):
                row[field] = row[field].split(', ') if row.get(field) else []

        # Log to RecommendationHistory if user_id provided; silent on failure
        if user_id and results:
            try:
                conn.start_transaction()
                for row in results:
                    cursor.execute("""
                        INSERT INTO RecommendationHistory (UserID, TrackID, GeneratedAt)
                        VALUES (%s, %s, NOW())
                    """, (user_id, row['TrackID']))
                conn.commit()
            except Exception:
                conn.rollback()

        return jsonify({
            'seed': {
                'track_id':   seed['TrackID'],
                'track_name': seed['TrackName'],
            },
            'result_count': len(results),
            'recommendations': results,
        }), 200

    finally:
        cursor.close()
        conn.close()


@recommendations_bp.route('/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    try:
        limit = max(1, int(request.args.get('limit', 50)))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be a positive integer'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                rh.HistoryID,
                rh.GeneratedAt,
                t.TrackID,
                t.TrackName,
                t.Popularity,
                al.AlbumName,
                GROUP_CONCAT(DISTINCT ar.ArtistName ORDER BY ar.ArtistName SEPARATOR ', ') AS Artists
            FROM RecommendationHistory rh
            JOIN Tracks         t  ON  t.TrackID  = rh.TrackID
            LEFT JOIN Albums    al ON al.AlbumID  = t.AlbumID
            LEFT JOIN TrackArtists ta ON ta.TrackID  = t.TrackID
            LEFT JOIN Artists      ar ON ar.ArtistID = ta.ArtistID
            WHERE rh.UserID = %s
            GROUP BY rh.HistoryID, rh.GeneratedAt, t.TrackID, t.TrackName, t.Popularity, al.AlbumName
            ORDER BY rh.GeneratedAt DESC
            LIMIT %s
        """, (user_id, limit))

        rows = cursor.fetchall()
        for row in rows:
            row['Artists'] = row['Artists'].split(', ') if row.get('Artists') else []

        return jsonify(rows), 200
    finally:
        cursor.close()
        conn.close()


@recommendations_bp.route('/history/all', methods=['DELETE'])
def clear_all_history():
    """Admin-only: wipe the entire RecommendationHistory table."""
    admin_id = request.args.get('user_id', type=int)
    if not admin_id:
        return jsonify({'error': 'user_id query parameter is required'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if not is_admin(cursor, admin_id):
            return jsonify({'error': 'Admin access required'}), 403

        conn.start_transaction()
        cursor.execute("DELETE FROM RecommendationHistory")
        deleted = cursor.rowcount
        conn.commit()
        return jsonify({'message': 'All recommendation history cleared', 'deleted_count': deleted}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@recommendations_bp.route('/history/<int:user_id>', methods=['DELETE'])
def clear_history(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "DELETE FROM RecommendationHistory WHERE UserID = %s",
            (user_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        return jsonify({'message': 'History cleared', 'deleted_count': deleted}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()
