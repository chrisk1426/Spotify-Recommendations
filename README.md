# Spotify Recommendations

A small Flask + MySQL backend for exploring a Kaggle Spotify dataset, plus a Textual terminal UI in `frontend/`.

The app can search tracks, show track details, recommend similar songs, search by mood profiles, create/generate playlists, view recommendation history, browse artists/albums/genres, and show simple analytics.

## Project structure

```text
backend/    Flask API, route handlers, database config
frontend/   Textual terminal UI
scripts/    Setup scripts
sql/        Schema, loader, indexes, database-user setup
data/       Kaggle Spotify CSV
```

## 1. Install Python packages

```bash
cd Spotify-Recommendations
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -e ./frontend
```

## 2. Check or start MySQL

Make sure a local MySQL server is running before loading the database. On this Mac install, the client is at:

```bash
/usr/local/mysql/bin/mysql --version
```

If MySQL is already running, you do not need to start it again. You can check with:

```bash
/usr/local/mysql/bin/mysqladmin -u root -p ping
```

If that says `mysqld is alive`, continue to the database setup step. If it is not running, start it from System Settings or with:

```bash
sudo /usr/local/mysql/support-files/mysql.server start
```

## 3. Load the database

Run the setup script from the repo root. It creates the schema, loads `data/dataset.csv`, adds indexes/constraints, creates the `spotify_api` user, and creates `backend/config.json` if it is missing.

This reloads the catalog data and truncates the app/user tables before inserting the dataset and starter mood profiles.

```bash
MYSQL_BIN=/usr/local/mysql/bin/mysql MYSQL_USER=root ./scripts/setup_database.sh
```

If your MySQL root user has a password:

```bash
MYSQL_BIN=/usr/local/mysql/bin/mysql MYSQL_USER=root MYSQL_PASSWORD='your_password' ./scripts/setup_database.sh
```

If MySQL rejects `LOAD DATA LOCAL INFILE`, enable it on the server and rerun the script:

```bash
/usr/local/mysql/bin/mysql -u root -p -e "SET GLOBAL local_infile = 1;"
```

## 4. Check backend config

The backend reads `backend/config.json`. The default file uses:

```json
{
  "localhost": {
    "host": "localhost",
    "user": "spotify_api",
    "password": "spotify_password",
    "database": "spotify_explorer",
    "secret_key": "change-me"
  }
}
```

Edit it if you used a different MySQL user or password.

## 5. Run the backend

```bash
source .venv/bin/activate
python backend/app.py
```

The API runs at `http://127.0.0.1:5000`.

## 6. Run the TUI

Open a second terminal:

```bash
source .venv/bin/activate
spotify-explorer-tui
```

If the backend is on a different URL:

```bash
SPOTIFY_API_URL=http://127.0.0.1:5000 spotify-explorer-tui
```

## Quick checks

With MySQL and the backend running:

```bash
curl http://127.0.0.1:5000/analytics/summary
curl "http://127.0.0.1:5000/tracks/?limit=3"
```
