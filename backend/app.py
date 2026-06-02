from flask import Flask
from config import DB_CONFIG

from routes.auth import auth_bp
from routes.playlists import playlists_bp
from routes.artists import artists_bp
from routes.tracks import tracks_bp
from routes.genres import genres_bp
from routes.albums import albums_bp
from routes.mood import mood_bp
from routes.analytics import analytics_bp
from routes.recommendations import recommendations_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = DB_CONFIG['secret_key']

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(playlists_bp, url_prefix='/playlists')
app.register_blueprint(artists_bp, url_prefix='/artists')
app.register_blueprint(tracks_bp, url_prefix='/tracks')
app.register_blueprint(genres_bp, url_prefix='/genres')
app.register_blueprint(albums_bp, url_prefix='/albums')
app.register_blueprint(mood_bp, url_prefix='/mood')
app.register_blueprint(analytics_bp, url_prefix='/analytics')
app.register_blueprint(recommendations_bp, url_prefix='/recommendations')

if __name__ == '__main__':
    app.run(debug=True)