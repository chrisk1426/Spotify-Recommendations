import mysql.connector
from config import DB_CONFIG

def get_connection():
    options = {
        'host': DB_CONFIG['host'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password'],
        'database': DB_CONFIG['database']
    }
    if DB_CONFIG.get('port'):
        options['port'] = DB_CONFIG['port']
    if DB_CONFIG.get('unix_socket'):
        options['unix_socket'] = DB_CONFIG['unix_socket']
    return mysql.connector.connect(**options)
