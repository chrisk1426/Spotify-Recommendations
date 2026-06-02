"""
Shared helper functions used across route blueprints.
"""


def check_playlist_owner(cursor, playlist_id, user_id):
    """
    Returns True  if user_id owns the playlist.
    Returns False if the playlist exists but belongs to someone else.
    Returns None  if the playlist does not exist.
    """
    cursor.execute(
        "SELECT UserID FROM Playlists WHERE PlaylistID = %s",
        (playlist_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return row['UserID'] == user_id


def is_admin(cursor, user_id):
    """Returns True if user_id exists and has IsAdmin = 1."""
    cursor.execute(
        "SELECT IsAdmin FROM Users WHERE UserID = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    return bool(row and row['IsAdmin'])
