from flask import Flask
from config import DB_CONFIG

from routes.auth import auth_bp
from routes.playlists import playlists_bp
from routes.artists import artists_bp
from routes.tracks import tracks_bp
from routes.genres import genres_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = DB_CONFIG['secret_key']

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(playlists_bp, url_prefix='/playlists')
app.register_blueprint(artists_bp, url_prefix='/artists')
app.register_blueprint(tracks_bp, url_prefix='/tracks')
app.register_blueprint(genres_bp, url_prefix='/genres')

if __name__ == '__main__':
    app.run(debug=True)