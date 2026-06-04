"""
Python file that contains API endpoints for user authentication.
"""
from flask import Blueprint, request, jsonify
from db import get_connection
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Endpoint to create/register a new user.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO Users (UserName, Password, IsAdmin) VALUES (%s, %s, 0)",
            (username, hashed.decode('utf-8'))
        )
        conn.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint to login as a user. Note that we hash passwords for security.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Users WHERE UserName = %s", (username,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['Password'].encode('utf-8')):
            return jsonify({'error': 'Invalid username or password'}), 401

        return jsonify({'message': 'Login successful', 'user_id': user['UserID'], 'is_admin': user['IsAdmin']}), 200
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    """
    Endpoint to get user/account information.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT UserID, UserName, IsAdmin FROM Users WHERE UserID = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify(user), 200
    finally:
        cursor.close()
        conn.close()