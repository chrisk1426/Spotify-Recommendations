# ============================================
# Final Project
# Name: Tyler Bruno
# Course: Dartmouth CS 61 Spring 2026
# ============================================

# Note: I decided to over-comment, because the reader may not be familiar with TUIs or the specific library.

from __future__ import annotations

from typing import Any, Callable, TypeVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Link,
    OptionList,
    ProgressBar,
    Rule,
    Select,
    Static,
    TabPane,
    TabbedContent,
)
from textual.widgets.option_list import Option

import data
from data import ApiError, format_duration, format_percent
from models import MoodProfile, Track


# This file is the main terminal UI. Textual apps are structured a lot like
# small web apps: we define a tree of widgets, attach event handlers to user
# actions, keep a little bit of local UI state, and refresh tables when that
# state changes. The backend still owns the real data. This file is mostly
# about presenting that data clearly inside a terminal.

T = TypeVar("T")

# Internal view IDs map to the human-readable names shown in the header. The
# ContentSwitcher below uses the same IDs to decide which screen is visible.
VIEW_IDS = {
    "account": "Account",
    "search": "Search",
    "recommendations": "Recommendations",
    "mood": "Mood Search",
    "playlists": "Playlists",
    "analytics": "Analytics",
    "catalog": "Catalog",
    "details": "Track Details",
}


class SpotifyExplorerApp(App[None]):
    """Main Textual application.

    Textual calls methods on this class during the app lifecycle. The important
    ones in this project are:
      - compose(): build the widgets that appear on screen
      - on_mount(): populate tables after the widgets exist
      - action_* and @on(...) handlers: respond to keyboard/mouse events

    The app intentionally keeps only UI/session state here. Anything that
    belongs in the database is requested through data.py.
    """

    TITLE = "Spotify Recommendations"
    SUB_TITLE = "backend connected"

    # BINDINGS define global keyboard shortcuts. Textual shows these in the
    # footer and calls matching action_* methods. For example, pressing "2"
    # calls action_show_view("search") because of the binding below.
    BINDINGS = [
        Binding("/", "focus_search", "Search", priority=True),
        Binding("1", "show_view('account')", "Account", priority=True),
        Binding("2", "show_view('search')", "Search", priority=True),
        Binding("3,r", "show_view('recommendations')", "Recommend", priority=True),
        Binding("4,m", "show_view('mood')", "Mood", priority=True),
        Binding("5,p", "show_view('playlists')", "Playlists", priority=True),
        Binding("6,a", "show_view('analytics')", "Analytics", priority=True),
        Binding("7,c", "show_view('catalog')", "Catalog", priority=True),
        Binding("8,d", "show_view('details')", "Details", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    # reactive() is Textual's watched state. When active_view changes,
    # watch_active_view() runs automatically. Same idea for selected_track_id.
    # This is how one track selection updates the inspector, details screen,
    # and recommendation seed without manually wiring every table together.
    active_view = reactive("account")
    selected_track_id = reactive(None)

    # Textual CSS is close to browser CSS, but it styles terminal widgets rather
    # than HTML. IDs like #sidebar refer to widget IDs set in compose(). Classes
    # like .card are reused for panels that need the same border/background.
    CSS = """
    Screen {
        background: #07100c;
        color: #e7f7ed;
    }

    Header {
        background: #072015;
        color: #e7f7ed;
        text-style: bold;
    }

    Footer {
        background: #06100b;
        color: #9bb8a6;
    }

    #shell {
        height: 1fr;
    }

    #sidebar {
        width: 27;
        height: 100%;
        background: #07110c;
        border-right: solid #116b3a;
        padding: 1;
    }

    #brand {
        height: 5;
        content-align: center middle;
        text-style: bold;
        color: #1ed760;
        border: tall #116b3a;
        margin-bottom: 1;
    }

    #global-status {
        min-height: 4;
    }

    #nav {
        height: 1fr;
        background: #07110c;
    }

    OptionList > .option-list--option {
        padding: 0 1;
    }

    OptionList > .option-list--option-highlighted {
        background: #123b27;
        color: #ffffff;
        text-style: bold;
    }

    #main-zone {
        width: 1fr;
        height: 100%;
    }

    #main-switcher {
        width: 1fr;
        height: 100%;
        background: #08120d;
    }

    .screen-panel {
        height: 100%;
        padding: 1;
    }

    #inspector {
        width: 38;
        min-width: 30;
        max-width: 44;
        height: 100%;
        background: #08140e;
        border-left: solid #116b3a;
        padding: 1;
    }

    .card {
        border: round #174d31;
        background: #0a1710;
        padding: 1;
        margin-bottom: 1;
    }

    .section-title {
        color: #1ed760;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    .muted {
        color: #7f9b8c;
    }

    .controls {
        height: auto;
        margin-bottom: 1;
    }

    .controls Input {
        width: 1fr;
        margin-right: 1;
    }

    .controls Select {
        width: 27;
        margin-right: 1;
    }

    .controls Button {
        width: auto;
        min-width: 11;
        margin-left: 1;
    }

    DataTable {
        height: 1fr;
        border: round #174d31;
        background: #08120d;
    }

    DataTable > .datatable--header {
        background: #0f2d1d;
        color: #b8ffd2;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1ed760 45%;
        color: #ffffff;
    }

    DataTable > .datatable--even-row {
        background: #09150f;
    }

    DataTable > .datatable--odd-row {
        background: #0d1b13;
    }

    TabbedContent {
        height: 1fr;
    }

    Tabs {
        height: 3;
    }

    Tab {
        color: #9bb8a6;
    }

    Tab.-active {
        color: #1ed760;
        text-style: bold;
    }

    ProgressBar {
        height: 1;
        margin-bottom: 1;
    }

    Bar > .bar--bar {
        color: #1ed760;
        background: #0f2d1d;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        # These values are frontend-only session state. They are not meant to
        # replace backend state. They just remember what the current user has
        # selected while the TUI is open.
        self.track_cache: dict[int, Track] = {}
        self.mood_profiles: list[MoodProfile] = []
        self.user_id: int | None = None
        self.username: str | None = None
        self.is_admin = False
        self.selected_playlist_id: int | None = None
        self.selected_playlist_track_id: int | None = None
        self._refreshing = False
        self._row_key_counter = 0

    def compose(self) -> ComposeResult:
        # compose() builds the widget tree. Think of this as the terminal
        # version of laying out HTML. The "yield" statements give Textual each
        # widget in order, and the nested "with" blocks say which widgets live
        # inside which containers.
        yield Header()
        with Horizontal(id="shell"):
            with Vertical(id="sidebar"):
                # Left sidebar: a static brand block, a status card, and a menu.
                # The Option IDs match VIEW_IDS and ContentSwitcher child IDs.
                yield Static("SPOTIFY\nRECOMMENDATIONS", id="brand")
                yield Static("Backend not checked yet.", id="global-status", classes="card")
                yield OptionList(
                    Option("1  Account", id="account"),
                    Option("2  Search", id="search"),
                    Option("3  Recommendations", id="recommendations"),
                    Option("4  Mood Search", id="mood"),
                    Option("5  Playlists", id="playlists"),
                    Option("6  Analytics", id="analytics"),
                    Option("7  Catalog", id="catalog"),
                    Option("8  Track Details", id="details"),
                    id="nav",
                )
            with Horizontal(id="main-zone"):
                # ContentSwitcher keeps all screens mounted but shows only one
                # at a time. This is cleaner than destroying/rebuilding screens
                # every time the user presses a number key.
                with ContentSwitcher(initial="account", id="main-switcher"):
                    yield from self._account_screen()
                    yield from self._search_screen()
                    yield from self._recommendations_screen()
                    yield from self._mood_screen()
                    yield from self._playlists_screen()
                    yield from self._analytics_screen()
                    yield from self._catalog_screen()
                    yield from self._details_screen()
                # The inspector stays visible no matter which main screen is
                # active. It gives users context about the selected track.
                yield from self._inspector()
        yield Footer()

    def _account_screen(self) -> ComposeResult:
        # Each *_screen method yields a self-contained page. Keeping screen
        # layout in helper methods makes compose() readable even though this app
        # has several different workflows.
        with Container(id="account", classes="screen-panel"):
            yield Static("Account", classes="section-title")
            with Horizontal(classes="controls"):
                yield Input(placeholder="Username", id="username")
                yield Input(placeholder="Password", password=True, id="password")
                yield Button("Login", id="login", variant="primary")
                yield Button("Register", id="register")
            yield Static(id="account-status", classes="card")
            yield DataTable(id="history-table", zebra_stripes=True)

    def _search_screen(self) -> ComposeResult:
        # Track search maps directly to GET /tracks/?q=...&limit=...
        # The table rows use hidden row keys so selecting a row can recover the
        # TrackID later without showing extra UI controls.
        with Container(id="search", classes="screen-panel"):
            yield Static("Track Search", classes="section-title")
            with Horizontal(classes="controls"):
                yield Input(placeholder="Track, artist, album, or genre", id="search-query")
                yield Input(value="50", placeholder="Limit", id="search-limit")
                yield Button("Search", id="run-search", variant="primary")
            yield DataTable(id="search-results", zebra_stripes=True)

    def _recommendations_screen(self) -> ComposeResult:
        # The recommendation screen needs a seed track. The Select starts with a
        # placeholder and is replaced with real tracks after search results load.
        with Container(id="recommendations", classes="screen-panel"):
            yield Static("Recommendations", classes="section-title")
            with Horizontal(classes="controls"):
                yield Select([("Load tracks first", 0)], value=0, allow_blank=False, id="seed-track")
                yield Input(value="10", placeholder="Limit", id="recommendation-limit")
                yield Button("Load", id="load-recommendations", variant="primary")
                yield Button("Clear History", id="clear-history")
            yield Static(id="recommendation-status", classes="card")
            yield DataTable(id="recommendation-results", zebra_stripes=True)

    def _mood_screen(self) -> ComposeResult:
        # Mood profiles are loaded from /mood/profiles on startup, then
        # /mood/search does the actual track lookup for the chosen mood.
        with Container(id="mood", classes="screen-panel"):
            yield Static("Mood Search", classes="section-title")
            with Horizontal(classes="controls"):
                yield Select([("Load moods first", 0)], value=0, allow_blank=False, id="mood-select")
                yield Input(value="50", placeholder="Limit", id="mood-limit")
                yield Button("Search", id="run-mood", variant="primary")
            yield Static(id="mood-profile", classes="card")
            yield DataTable(id="mood-results", zebra_stripes=True)

    def _playlists_screen(self) -> ComposeResult:
        # Playlist actions require a logged-in user because the backend checks
        # playlist ownership with user_id. The TUI keeps the current user_id
        # after login and sends it with create/add/remove/delete requests.
        with Container(id="playlists", classes="screen-panel"):
            yield Static("Playlists", classes="section-title")
            with Horizontal(classes="controls"):
                yield Input(value="My Playlist", placeholder="Playlist name", id="playlist-name")
                yield Select([("No mood", 0)], value=0, allow_blank=False, id="playlist-mood")
                yield Input(value="20", placeholder="Limit", id="playlist-limit")
                yield Button("Create", id="create-playlist", variant="primary")
                yield Button("Generate", id="generate-playlist")
            with Horizontal(classes="controls"):
                yield Button("Refresh", id="refresh-playlists")
                yield Button("Add Selected Track", id="add-selected-track")
                yield Button("Remove Row Track", id="remove-playlist-track")
                yield Button("Delete Playlist", id="delete-playlist")
            yield Static(id="playlist-status", classes="card")
            with Horizontal():
                yield DataTable(id="playlist-table", zebra_stripes=True)
                yield DataTable(id="playlist-tracks", zebra_stripes=True)

    def _analytics_screen(self) -> ComposeResult:
        # Analytics are read-only summaries over the whole dataset. TabbedContent
        # keeps the screen compact while still exposing all backend analytics
        # endpoints from one place.
        with Container(id="analytics", classes="screen-panel"):
            yield Static("Analytics", classes="section-title")
            yield Static(id="analytics-summary", classes="card")
            with TabbedContent(initial="popular-genres"):
                with TabPane("Popularity", id="popular-genres"):
                    yield DataTable(id="popularity-genres", zebra_stripes=True)
                with TabPane("Energy", id="energy-genres"):
                    yield DataTable(id="energy-genres-table", zebra_stripes=True)
                with TabPane("Valence", id="valence-genres"):
                    yield DataTable(id="valence-genres-table", zebra_stripes=True)
                with TabPane("BPM", id="bpm-tab"):
                    yield DataTable(id="bpm-table", zebra_stripes=True)
                with TabPane("Danceability", id="dance-tab"):
                    yield DataTable(id="dance-table", zebra_stripes=True)

    def _catalog_screen(self) -> ComposeResult:
        # Catalog is a lightweight browser for artists, albums, and genres.
        # Selecting one of those rows loads related tracks into the Tracks tab.
        with Container(id="catalog", classes="screen-panel"):
            yield Static("Catalog", classes="section-title")
            with Horizontal(classes="controls"):
                yield Input(placeholder="Artist or album search", id="catalog-query")
                yield Button("Refresh", id="refresh-catalog", variant="primary")
            with TabbedContent(initial="artists-tab"):
                with TabPane("Artists", id="artists-tab"):
                    yield DataTable(id="artists-table", zebra_stripes=True)
                with TabPane("Albums", id="albums-tab"):
                    yield DataTable(id="albums-table", zebra_stripes=True)
                with TabPane("Genres", id="genres-tab"):
                    yield DataTable(id="genres-table", zebra_stripes=True)
                with TabPane("Tracks", id="catalog-tracks-tab"):
                    yield DataTable(id="catalog-tracks", zebra_stripes=True)

    def _details_screen(self) -> ComposeResult:
        # Track Details is driven entirely by selected_track_id. Any table that
        # selects a track can update this page.
        with Container(id="details", classes="screen-panel"):
            yield Static("Track Details", classes="section-title")
            yield Static(id="detail-overview-copy", classes="card")
            yield Link("Open Spotify track", url="https://open.spotify.com/", id="detail-link")
            with TabbedContent(initial="detail-features"):
                with TabPane("Audio features", id="detail-features"):
                    yield DataTable(id="feature-table", zebra_stripes=True)
                with TabPane("Similar tracks", id="detail-similar"):
                    yield DataTable(id="detail-similar-table", zebra_stripes=True)

    def _inspector(self) -> ComposeResult:
        # The inspector is a persistent side panel. It is useful in a terminal
        # app because table rows can be dense. The side panel lets the user keep
        # a selected track in view while moving between screens.
        with VerticalScroll(id="inspector"):
            yield Static("Now selected", classes="section-title")
            yield Static(id="selected-title", classes="card")
            yield Rule()
            yield Static("Audio profile", classes="section-title")
            yield Label("Energy", classes="muted")
            yield ProgressBar(total=100, show_eta=False, id="meter-energy")
            yield Label("Danceability", classes="muted")
            yield ProgressBar(total=100, show_eta=False, id="meter-dance")
            yield Label("Valence", classes="muted")
            yield ProgressBar(total=100, show_eta=False, id="meter-valence")
            yield Label("Acousticness", classes="muted")
            yield ProgressBar(total=100, show_eta=False, id="meter-acoustic")
            yield Static(id="selected-metadata", classes="card")

    def on_mount(self) -> None:
        # on_mount() runs after compose() has finished and the widgets actually
        # exist. That matters because query_one("#some-id") only works after
        # Textual has mounted the widget tree.
        self._setup_tables()

        # _refreshing is a guard flag. While we are filling tables, Textual may
        # emit selection/change events. We do not want those startup events to
        # behave like user clicks, so event handlers check this flag and return.
        self._refreshing = True
        try:
            # The first refresh attempts several backend calls. If the backend
            # is not running, _safe() displays a clear status message instead
            # of crashing the TUI.
            self._load_moods()
            self._refresh_search_table()
            self._refresh_analytics()
            self._refresh_catalog()
            self._refresh_account()
            self._refresh_inspector()
            self._refresh_details()
        finally:
            self._refreshing = False

    def _setup_tables(self) -> None:
        # DataTable columns are declared once. Later refresh methods only clear
        # rows and add new rows. They do not rebuild table structure.
        self._table("#history-table").add_columns("Track", "Artist", "Generated")
        self._table("#search-results").add_columns("ID", "Track", "Artist", "Album", "Genre", "Pop", "BPM")
        self._table("#recommendation-results").add_columns("Score", "ID", "Track", "Artist", "Genre", "Pop", "BPM")
        self._table("#mood-results").add_columns("ID", "Track", "Artist", "Album", "Pop", "Energy", "Tempo")
        self._table("#playlist-table").add_columns("ID", "Name", "Mood", "Created", "Updated")
        self._table("#playlist-tracks").add_columns("ID", "Track", "Popularity", "Duration")
        self._table("#popularity-genres").add_columns("Genre", "Tracks", "Avg Popularity")
        self._table("#energy-genres-table").add_columns("Genre", "Tracks", "Avg Energy")
        self._table("#valence-genres-table").add_columns("Genre", "Tracks", "Avg Valence")
        self._table("#bpm-table").add_columns("Range", "Tracks")
        self._table("#dance-table").add_columns("ID", "Track", "Popularity", "Dance", "Energy", "Valence")
        self._table("#artists-table").add_columns("ID", "Artist", "Tracks")
        self._table("#albums-table").add_columns("ID", "Album", "Tracks")
        self._table("#genres-table").add_columns("ID", "Genre")
        self._table("#catalog-tracks").add_columns("ID", "Track", "Artist", "Album", "Pop")
        self._table("#feature-table").add_columns("Feature", "Value")
        self._table("#detail-similar-table").add_columns("Score", "ID", "Track", "Artist")
        for table in self.query(DataTable):
            # A row cursor makes table navigation behave like selecting records,
            # which is a better fit here than selecting individual cells.
            table.cursor_type = "row"
            table.zebra_stripes = True

    def _table(self, selector: str) -> DataTable:
        # Small convenience wrapper so refresh methods read cleanly:
        # self._table("#search-results") is shorter than repeating query_one.
        return self.query_one(selector, DataTable)

    def _safe(self, label: str, func: Callable[[], T], fallback: T) -> T:
        # All backend calls go through this wrapper. If the Flask server is down
        # or an endpoint returns an error, data.py raises ApiError. Catching it
        # here keeps every screen from needing its own try/except block.
        try:
            result = func()
        except ApiError as error:
            self._set_status(f"{label}: {error}")
            return fallback
        self._set_status(f"Connected to {data.API_BASE_URL}")
        return result

    def _set_status(self, message: str) -> None:
        # The global status card is our central place for backend connection
        # feedback. NoMatches can happen during early startup, before the status
        # widget exists, so this method quietly ignores that case.
        try:
            self.query_one("#global-status", Static).update(message)
        except NoMatches:
            pass

    def _input_int(self, selector: str, default: int, minimum: int = 1, maximum: int = 200) -> int:
        # User-entered limits are strings. This helper turns them into safe
        # integer bounds before passing them to the backend.
        try:
            value = int(self.query_one(selector, Input).value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    def _make_row_key(self, prefix: str, row_id: int) -> str:
        # Textual row keys need to be unique. We encode the record type and ID
        # in the key, then append a counter so duplicate TrackIDs can appear in
        # multiple tables without colliding.
        self._row_key_counter += 1
        return f"{prefix}:{row_id}:{self._row_key_counter}"

    def _row_key_value(self, row_key: object) -> str:
        # Textual wraps row keys in objects. This normalizes either the wrapper
        # or a plain string into one string that on_table_row_selected can parse.
        value = getattr(row_key, "value", None)
        return str(value if value is not None else row_key)

    def _cache_tracks(self, tracks: list[Track]) -> None:
        # Many backend list endpoints return partial track rows. Caching lets us
        # reuse the best version we have for inspector/details without making a
        # fresh GET /tracks/<id> every time a user clicks around.
        for track in tracks:
            self.track_cache[track.track_id] = track

    def _selected_track(self) -> Track | None:
        # selected_track_id is just an integer. This method turns it into a
        # Track object, fetching from the backend if the cache does not already
        # have it.
        if self.selected_track_id is None:
            return None
        track_id = int(self.selected_track_id)
        if track_id not in self.track_cache:
            track = self._safe("Track details", lambda: data.get_track(track_id), None)
            if track:
                self.track_cache[track.track_id] = track
        return self.track_cache.get(track_id)

    def _load_moods(self) -> None:
        # Mood profiles are needed in two places: mood search and generated
        # playlists. We load them once and use the same options in both Selects.
        profiles = self._safe("Mood profiles", data.list_mood_profiles, [])
        self.mood_profiles = profiles
        mood_options = [(profile.name, profile.mood_id) for profile in profiles] or [("No moods loaded", 0)]
        self._set_select_options("#mood-select", mood_options)
        self._set_select_options("#playlist-mood", [("No mood", 0), *mood_options])
        self._refresh_mood_profile_copy()

    def _set_select_options(self, selector: str, options: list[tuple[str, int]]) -> None:
        # Textual Select options are (label, value) pairs. When the option list
        # changes, we preserve the old value if it still exists. Otherwise we
        # fall back to the first option.
        select = self.query_one(selector, Select)
        current = select.value
        select.set_options(options)
        values = {value for _, value in options}
        select.value = current if current in values else options[0][1]

    def _update_seed_options(self, tracks: list[Track]) -> None:
        # The recommendation seed dropdown uses search results. That means users
        # can search for a known track first, then immediately ask for similar
        # songs from that seed.
        if not tracks:
            return
        options = [(f"{track.name} - {self._artist_text(track)}", track.track_id) for track in tracks[:50]]
        self._set_select_options("#seed-track", options)

    def _artist_text(self, track: Track) -> str:
        # Artists are stored as a tuple so tracks with multiple artists display
        # naturally in tables.
        return ", ".join(track.artists) if track.artists else "Unknown artist"

    def _genre_text(self, track: Track) -> str:
        return ", ".join(track.genres) if track.genres else ""

    def watch_active_view(self, view_id: str) -> None:
        # Textual automatically calls watch_<reactive_name> when that reactive
        # value changes. This keeps the sidebar/menu shortcuts simple: setting
        # self.active_view is enough to swap the visible screen.
        if not self.is_mounted:
            return
        try:
            self.query_one("#main-switcher", ContentSwitcher).current = view_id
        except NoMatches:
            return
        self.sub_title = VIEW_IDS[view_id]

    def watch_selected_track_id(self, _track_id: int | None) -> None:
        # A selected track is shared state across the app. Once it changes we
        # refresh every UI area that depends on it: inspector, details page, and
        # recommendation seed dropdown.
        if not self.is_mounted or self._refreshing:
            return
        track = self._selected_track()
        if track:
            seed = self.query_one("#seed-track", Select)
            if seed.value != track.track_id:
                try:
                    seed.value = track.track_id
                except Exception:
                    pass
        self._refresh_inspector()
        self._refresh_details()

    def action_show_view(self, view_id: str) -> None:
        # Called by keyboard bindings and SearchInput-like navigation.
        self.active_view = view_id

    def action_focus_search(self) -> None:
        # "/" is a common search shortcut. It switches to the search screen and
        # places the cursor in the search input.
        self.active_view = "search"
        self.query_one("#search-query", Input).focus()

    @on(OptionList.OptionSelected, "#nav")
    def on_nav_selected(self, event: OptionList.OptionSelected) -> None:
        # Sidebar navigation. The option_id is the same string used by
        # ContentSwitcher, so selecting an option is just setting active_view.
        if event.option_id:
            self.active_view = event.option_id

    @on(Button.Pressed, "#login")
    def on_login(self) -> None:
        # Login stores only the returned user_id/admin flag locally. There is no
        # token system in this backend, so later playlist/history calls include
        # user_id directly.
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not username or not password:
            self.query_one("#account-status", Static).update("Username and password are required.")
            return
        response = self._safe("Login", lambda: data.login(username, password), None)
        if not response:
            return
        self.user_id = int(response["user_id"])
        self.username = username
        self.is_admin = bool(response.get("is_admin"))
        self._refresh_account()
        self._refresh_playlists()
        self.notify(f"Logged in as {username}", title="Account")

    @on(Button.Pressed, "#register")
    def on_register(self) -> None:
        # Register creates the account but does not automatically log in. That
        # keeps the flow aligned with the backend's separate /register and
        # /login endpoints.
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not username or not password:
            self.query_one("#account-status", Static).update("Username and password are required.")
            return
        response = self._safe("Register", lambda: data.register(username, password), None)
        if response:
            self.query_one("#account-status", Static).update("Registered. Log in with the same credentials.")

    @on(Button.Pressed, "#run-search")
    def on_run_search(self) -> None:
        # Button version of search.
        self._refresh_search_table()

    @on(Input.Submitted, "#search-query")
    def on_search_submitted(self) -> None:
        # Pressing Enter in the search input should feel the same as pressing
        # the Search button.
        self._refresh_search_table()

    @on(Button.Pressed, "#load-recommendations")
    def on_load_recommendations(self) -> None:
        # Re-query recommendations for whichever seed track is currently chosen.
        self._refresh_recommendations()

    @on(Button.Pressed, "#clear-history")
    def on_clear_history(self) -> None:
        # Recommendation history belongs to a user, so anonymous users cannot
        # clear anything. This mirrors the backend route shape.
        if self.user_id is None:
            self.query_one("#recommendation-status", Static).update("Log in before clearing recommendation history.")
            return
        response = self._safe("Clear history", lambda: data.clear_recommendation_history(self.user_id), None)
        if response:
            self.query_one("#recommendation-status", Static).update(response.get("message", "History cleared."))
            self._refresh_account()

    @on(Button.Pressed, "#run-mood")
    def on_run_mood(self) -> None:
        # Mood search is intentionally explicit instead of live-updating on
        # every change because the backend query can touch a large dataset.
        self._refresh_mood()

    @on(Button.Pressed, "#create-playlist")
    def on_create_playlist(self) -> None:
        # Create an empty playlist, optionally linked to a mood profile. Tracks
        # can be added later from whichever table row is selected.
        if self.user_id is None:
            self.query_one("#playlist-status", Static).update("Log in before creating playlists.")
            return
        name = self.query_one("#playlist-name", Input).value.strip() or "Untitled Playlist"
        mood_id = int(self.query_one("#playlist-mood", Select).value or 0) or None
        response = self._safe("Create playlist", lambda: data.create_playlist(self.user_id, name, mood_id), None)
        if response:
            self.selected_playlist_id = int(response["playlist_id"])
            self._refresh_playlists()
            self.notify("Playlist created", title="Playlists")

    @on(Button.Pressed, "#generate-playlist")
    def on_generate_playlist(self) -> None:
        # Generate delegates the actual track choice to the backend. The TUI
        # only sends user_id, mood_profile_id, name, and limit.
        if self.user_id is None:
            self.query_one("#playlist-status", Static).update("Log in before generating playlists.")
            return
        mood_id = int(self.query_one("#playlist-mood", Select).value or 0)
        if not mood_id:
            self.query_one("#playlist-status", Static).update("Choose a mood before generating a playlist.")
            return
        name = self.query_one("#playlist-name", Input).value.strip() or "Generated Playlist"
        limit = self._input_int("#playlist-limit", 20, maximum=50)
        response = self._safe("Generate playlist", lambda: data.generate_playlist(self.user_id, mood_id, name, limit), None)
        if response:
            self.selected_playlist_id = int(response["playlist_id"])
            self._refresh_playlists()
            self.notify("Playlist generated", title="Playlists")

    @on(Button.Pressed, "#refresh-playlists")
    def on_refresh_playlists(self) -> None:
        # Manual refresh is useful after creating/generating/deleting playlists
        # or if another client has changed the same user's data.
        self._refresh_playlists()

    @on(Button.Pressed, "#add-selected-track")
    def on_add_selected_track(self) -> None:
        # Adding a track requires three pieces of state: logged-in user, selected
        # playlist, and selected track. If any is missing, show a plain message
        # instead of sending a bad request to Flask.
        if self.user_id is None or self.selected_playlist_id is None or self.selected_track_id is None:
            self.query_one("#playlist-status", Static).update("Log in, select a playlist, and select a track first.")
            return
        response = self._safe(
            "Add track",
            lambda: data.add_playlist_track(self.selected_playlist_id, self.user_id, int(self.selected_track_id)),
            None,
        )
        if response:
            self._refresh_playlist_tracks()
            self.notify("Track added", title="Playlists")

    @on(Button.Pressed, "#remove-playlist-track")
    def on_remove_playlist_track(self) -> None:
        # The remove button acts on the selected row in the playlist-tracks
        # table, not merely the global selected track. That avoids deleting the
        # wrong row after the user has clicked elsewhere.
        if self.user_id is None or self.selected_playlist_id is None or self.selected_playlist_track_id is None:
            self.query_one("#playlist-status", Static).update("Select a playlist track row first.")
            return
        response = self._safe(
            "Remove track",
            lambda: data.remove_playlist_track(
                self.selected_playlist_id,
                self.user_id,
                self.selected_playlist_track_id,
            ),
            None,
        )
        if response:
            self.selected_playlist_track_id = None
            self._refresh_playlist_tracks()

    @on(Button.Pressed, "#delete-playlist")
    def on_delete_playlist(self) -> None:
        # Delete removes the selected playlist. The backend enforces ownership
        # using user_id, so this button is safe even if a user guesses an ID.
        if self.user_id is None or self.selected_playlist_id is None:
            self.query_one("#playlist-status", Static).update("Select a playlist first.")
            return
        response = self._safe(
            "Delete playlist",
            lambda: data.delete_playlist(self.selected_playlist_id, self.user_id),
            None,
        )
        if response:
            self.selected_playlist_id = None
            self._refresh_playlists()

    @on(Button.Pressed, "#refresh-catalog")
    def on_refresh_catalog(self) -> None:
        # Refresh artists/albums/genres using the current catalog search box.
        self._refresh_catalog()

    @on(Select.Changed, "#seed-track")
    def on_seed_changed(self, event: Select.Changed) -> None:
        # Keep the app-wide selected track synchronized with the recommendation
        # seed dropdown. This also updates the inspector/details.
        if event.value:
            self.selected_track_id = int(event.value)

    @on(Select.Changed, "#mood-select")
    def on_mood_changed(self) -> None:
        # Changing the mood dropdown updates the range explanation immediately.
        # actual track search still waits for the Search button.
        self._refresh_mood_profile_copy()

    @on(DataTable.RowSelected)
    def on_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # This is the central table-click handler for the whole app. Every row
        # key starts with a prefix like "track", "playlist", or "artist".
        # That prefix tells us what kind of object was selected and what to do.
        if self._refreshing:
            return
        key = self._row_key_value(event.row_key)
        parts = key.split(":")
        if len(parts) < 2:
            return
        kind = parts[0]
        try:
            row_id = int(parts[1])
        except ValueError:
            return

        if kind == "track":
            # Track rows drive inspector/details/recommendation seed.
            self.selected_track_id = row_id
        elif kind == "playlist":
            # Playlist rows load their track list on the right.
            self.selected_playlist_id = row_id
            self._refresh_playlist_tracks()
        elif kind == "playlist-track":
            # Playlist-track rows are both removable playlist entries and normal
            # track selections for the inspector/details panel.
            self.selected_playlist_track_id = row_id
            self.selected_track_id = row_id
        elif kind == "artist":
            # Artist/album/genre rows load related tracks into the catalog tab.
            self._load_artist_tracks(row_id)
        elif kind == "album":
            self._load_album_tracks(row_id)
        elif kind == "genre":
            self._load_genre_tracks(row_id)

    def _refresh_account(self) -> None:
        # Account refresh updates two things: the login status card and the
        # user's recommendation history table. If nobody is logged in, we clear
        # history because there is no user_id to query.
        status = self.query_one("#account-status", Static)
        if self.user_id is None:
            status.update("Not logged in. Login enables playlists and recommendation history.")
            self._table("#history-table").clear()
            return
        admin = "yes" if self.is_admin else "no"
        status.update(f"Logged in as {self.username}  |  user_id {self.user_id}  |  admin {admin}")
        rows = self._safe("Recommendation history", lambda: data.get_recommendation_history(self.user_id), [])
        table = self._table("#history-table")
        table.clear()
        for row in rows:
            track = row["track"]
            # data.py attaches a parsed Track object to each raw history row so
            # the UI can show normal track fields while preserving GeneratedAt.
            table.add_row(
                track.name,
                self._artist_text(track),
                str(row.get("GeneratedAt") or ""),
                key=self._make_row_key("track", track.track_id),
            )

    def _refresh_search_table(self) -> None:
        # Search is the main entry point into the catalog. The backend searches
        # track name, album, artist, and genre. Results are cached because later
        # screens may need the same tracks.
        query = self.query_one("#search-query", Input).value
        limit = self._input_int("#search-limit", 50, maximum=200)
        tracks = self._safe("Track search", lambda: data.list_tracks(query, limit), [])
        self._cache_tracks(tracks)
        self._update_seed_options(tracks)
        if tracks and self.selected_track_id is None:
            # Pick a default selected track so the inspector is not empty after
            # the first successful search.
            self.selected_track_id = tracks[0].track_id

        table = self._table("#search-results")
        table.clear()
        for track in tracks:
            table.add_row(
                str(track.track_id),
                track.name,
                self._artist_text(track),
                track.album,
                self._genre_text(track),
                str(track.popularity),
                f"{track.features.tempo:.0f}",
                key=self._make_row_key("track", track.track_id),
            )

    def _refresh_recommendations(self) -> None:
        # Recommendations require a seed TrackID. When user_id is present, the
        # backend also records the generated recommendation rows in history.
        track_id = int(self.query_one("#seed-track", Select).value or 0)
        if not track_id:
            self.query_one("#recommendation-status", Static).update("Search tracks first, then choose a seed track.")
            return
        limit = self._input_int("#recommendation-limit", 10, maximum=50)
        user_id = self.user_id
        rows = self._safe(
            "Recommendations",
            lambda: data.get_recommendations(track_id, limit, user_id),
            [],
        )
        self._cache_tracks([row.track for row in rows])
        self.query_one("#recommendation-status", Static).update(
            "Recommendation results are logged to history when logged in."
            if self.user_id is not None
            else "Log in to store recommendation history."
        )
        table = self._table("#recommendation-results")
        table.clear()
        for row in rows:
            # SimilarityScore comes from the backend SQL formula. Keeping it in
            # the first column makes the ranking easy to scan.
            table.add_row(
                f"{row.score:.3f}",
                str(row.track.track_id),
                row.track.name,
                self._artist_text(row.track),
                self._genre_text(row.track),
                str(row.track.popularity),
                f"{row.track.features.tempo:.0f}",
                key=self._make_row_key("track", row.track.track_id),
            )
        self._refresh_account()

    def _refresh_mood_profile_copy(self) -> None:
        # This updates only the explanatory card for the selected mood. It does
        # not ask the backend for tracks.
        mood_id = int(self.query_one("#mood-select", Select).value or 0)
        profile = self._mood_by_id(mood_id)
        self.query_one("#mood-profile", Static).update(self._mood_copy(profile, None))

    def _refresh_mood(self) -> None:
        # Mood search uses backend-defined ranges stored in MoodProfiles. The
        # frontend does not reimplement those filters. It simply chooses a mood
        # name and displays the tracks returned by /mood/search.
        mood_id = int(self.query_one("#mood-select", Select).value or 0)
        profile = self._mood_by_id(mood_id)
        if profile is None:
            self.query_one("#mood-profile", Static).update("No mood profile loaded.")
            return
        limit = self._input_int("#mood-limit", 50, maximum=200)
        _response_profile, tracks = self._safe("Mood search", lambda: data.search_mood(profile.name, limit), (None, []))
        self._cache_tracks(tracks)
        self.query_one("#mood-profile", Static).update(self._mood_copy(profile, len(tracks)))
        table = self._table("#mood-results")
        table.clear()
        for track in tracks:
            table.add_row(
                str(track.track_id),
                track.name,
                self._artist_text(track),
                track.album,
                str(track.popularity),
                format_percent(track.features.energy),
                f"{track.features.tempo:.0f}",
                key=self._make_row_key("track", track.track_id),
            )

    def _refresh_playlists(self) -> None:
        # Load all playlists owned by the logged-in user. The selected playlist
        # then drives _refresh_playlist_tracks().
        status = self.query_one("#playlist-status", Static)
        table = self._table("#playlist-table")
        table.clear()
        self._table("#playlist-tracks").clear()
        if self.user_id is None:
            status.update("Log in to create, generate, edit, and delete playlists.")
            return
        playlists = self._safe("Playlists", lambda: data.list_user_playlists(self.user_id), [])
        if playlists and self.selected_playlist_id is None:
            # If there is no active playlist yet, default to the first one so
            # the right-hand tracks table can show something useful.
            self.selected_playlist_id = int(playlists[0]["PlaylistID"])
        for playlist in playlists:
            table.add_row(
                str(playlist.get("PlaylistID", "")),
                str(playlist.get("PlaylistName", "")),
                str(playlist.get("MoodProfileID") or ""),
                str(playlist.get("CreatedAt") or ""),
                str(playlist.get("UpdatedAt") or ""),
                key=self._make_row_key("playlist", int(playlist["PlaylistID"])),
            )
        status.update(f"{len(playlists)} playlist(s) loaded.")
        self._refresh_playlist_tracks()

    def _refresh_playlist_tracks(self) -> None:
        # The backend playlist track endpoint returns a smaller track shape than
        # full track details. data.py still maps it into Track so the table code
        # can treat all track rows consistently.
        table = self._table("#playlist-tracks")
        table.clear()
        if self.selected_playlist_id is None:
            return
        tracks = self._safe("Playlist tracks", lambda: data.get_playlist_tracks(self.selected_playlist_id), [])
        self._cache_tracks(tracks)
        for track in tracks:
            table.add_row(
                str(track.track_id),
                track.name,
                str(track.popularity),
                format_duration(track.duration_ms),
                key=self._make_row_key("playlist-track", track.track_id),
            )

    def _refresh_analytics(self) -> None:
        # Analytics calls are independent read-only endpoints. If one fails,
        # _safe() leaves that table empty but the rest of the app still opens.
        summary = self._safe("Analytics summary", data.analytics_summary, {})
        self.query_one("#analytics-summary", Static).update(self._summary_copy(summary))
        self._fill_metric_table("#popularity-genres", data.popularity_by_genre, "AvgPopularity")
        self._fill_metric_table("#energy-genres-table", data.energetic_genres, "AvgEnergy")
        self._fill_metric_table("#valence-genres-table", data.valence_by_genre, "AvgValence")

        bpm_rows = self._safe("BPM distribution", data.bpm_distribution, [])
        bpm_table = self._table("#bpm-table")
        bpm_table.clear()
        for row in bpm_rows:
            # The BPM endpoint already returns bucket min/max values, so the TUI
            # only formats them into a readable range.
            bpm_table.add_row(
                f"{row.get('BucketMin')}-{row.get('BucketMax')}",
                str(row.get("TrackCount", "")),
            )

        dance_rows = self._safe("Danceability sample", data.popularity_vs_danceability, [])
        dance_table = self._table("#dance-table")
        dance_table.clear()
        for row in dance_rows[:100]:
            # This sample can be large. The table only shows the first 100 rows
            # even if the backend returns more.
            track_id = int(row.get("TrackID", 0))
            dance_table.add_row(
                str(track_id),
                str(row.get("TrackName", "")),
                str(row.get("Popularity", "")),
                format_percent(float(row.get("Danceability") or 0)),
                format_percent(float(row.get("Energy") or 0)),
                format_percent(float(row.get("Valence") or 0)),
                key=self._make_row_key("track", track_id),
            )

    def _fill_metric_table(
        self,
        selector: str,
        fetcher: Callable[[int], list[dict[str, Any]]],
        metric_key: str,
    ) -> None:
        # Energy, valence, and popularity-by-genre all have the same table
        # shape: GenreName, TrackCount, and one metric. This helper avoids
        # writing the same table-clearing loop three times.
        rows = self._safe(selector, lambda: fetcher(20), [])
        table = self._table(selector)
        table.clear()
        for row in rows:
            metric = row.get(metric_key)
            metric_text = f"{float(metric):.3f}" if metric is not None else ""
            table.add_row(str(row.get("GenreName", "")), str(row.get("TrackCount", "")), metric_text)

    def _refresh_catalog(self) -> None:
        # Catalog refresh fills three independent lookup tables. The fourth tab,
        # Tracks, is populated only after the user selects an artist/album/genre.
        query = self.query_one("#catalog-query", Input).value
        artists = self._safe("Artists", lambda: data.list_artists(query), [])
        albums = self._safe("Albums", lambda: data.list_albums(query), [])
        genres = self._safe("Genres", data.list_genres, [])

        artists_table = self._table("#artists-table")
        artists_table.clear()
        for artist in artists:
            artist_id = int(artist.get("ArtistID", 0))
            artists_table.add_row(
                str(artist_id),
                str(artist.get("ArtistName", "")),
                str(artist.get("TrackCount", "")),
                key=self._make_row_key("artist", artist_id),
            )

        albums_table = self._table("#albums-table")
        albums_table.clear()
        for album in albums:
            album_id = int(album.get("AlbumID", 0))
            albums_table.add_row(
                str(album_id),
                str(album.get("AlbumName", "")),
                str(album.get("TrackCount", "")),
                key=self._make_row_key("album", album_id),
            )

        genres_table = self._table("#genres-table")
        genres_table.clear()
        for genre in genres:
            genre_id = int(genre.get("GenreID", 0))
            genres_table.add_row(
                str(genre_id),
                str(genre.get("GenreName", "")),
                key=self._make_row_key("genre", genre_id),
            )

    def _load_artist_tracks(self, artist_id: int) -> None:
        # The artist detail endpoint nests tracks under an artist object. It
        # does not include an Artists list on each track, so we add the selected
        # artist name before passing the row through the normal mapper.
        artist = self._safe("Artist tracks", lambda: data.get_artist(artist_id), None)
        tracks = []
        if artist:
            artist_name = str(artist.get("ArtistName") or "")
            for row in artist.get("tracks", []):
                row.setdefault("Artists", [artist_name])
                tracks.append(data.track_from_row(row))
        self._fill_catalog_tracks(tracks)

    def _load_album_tracks(self, album_id: int) -> None:
        # Album tracks already have the fuller joined shape, so they can be
        # mapped directly.
        tracks = self._safe("Album tracks", lambda: data.get_album_tracks(album_id), [])
        self._fill_catalog_tracks(tracks)

    def _load_genre_tracks(self, genre_id: int) -> None:
        # Genre tracks are returned by a compact endpoint. We look up the genre
        # name separately so the inspector/details still have a genre label.
        genre_name = ""
        for genre in self._safe("Genres", data.list_genres, []):
            if int(genre.get("GenreID", 0)) == genre_id:
                genre_name = str(genre.get("GenreName") or "")
                break
        tracks = self._safe("Genre tracks", lambda: data.get_genre_tracks(genre_id), [])
        if genre_name:
            tracks = [
                Track(
                    track_id=track.track_id,
                    name=track.name,
                    artists=track.artists,
                    album=track.album,
                    genres=(genre_name,),
                    duration_ms=track.duration_ms,
                    popularity=track.popularity,
                    explicit=track.explicit,
                    features=track.features,
                    spotify_track_id=track.spotify_track_id,
                )
                for track in tracks
            ]
        self._fill_catalog_tracks(tracks)

    def _fill_catalog_tracks(self, tracks: list[Track]) -> None:
        # Shared rendering for whichever catalog relationship was selected.
        self._cache_tracks(tracks)
        table = self._table("#catalog-tracks")
        table.clear()
        for track in tracks:
            table.add_row(
                str(track.track_id),
                track.name,
                self._artist_text(track),
                track.album,
                str(track.popularity),
                key=self._make_row_key("track", track.track_id),
            )

    def _refresh_details(self) -> None:
        # Details is the most complete view of a selected track. It combines
        # static metadata, raw audio features, and a small recommendation list.
        track = self._selected_track()
        if track is None:
            self.query_one("#detail-overview-copy", Static).update("Select a track to see details.")
            self._table("#feature-table").clear()
            self._table("#detail-similar-table").clear()
            return

        self.query_one("#detail-overview-copy", Static).update(self._track_detail_markup(track))
        self.query_one("#detail-link", Link).url = track.spotify_url

        # These rows explain the same audio fields the backend uses for mood
        # search and recommendation scoring. Percent formatting is easier to
        # read in a UI than raw decimals like 0.734.
        feature_rows = (
            ("Danceability", format_percent(track.features.danceability)),
            ("Energy", format_percent(track.features.energy)),
            ("Valence", format_percent(track.features.valence)),
            ("Acousticness", format_percent(track.features.acousticness)),
            ("Speechiness", format_percent(track.features.speechiness)),
            ("Instrumentalness", format_percent(track.features.instrumentalness)),
            ("Liveness", format_percent(track.features.liveness)),
            ("Tempo", f"{track.features.tempo:.0f} BPM"),
            ("Loudness", f"{track.features.loudness:.1f} dB"),
        )
        feature_table = self._table("#feature-table")
        feature_table.clear()
        for name, value in feature_rows:
            feature_table.add_row(name, value)

        rows = self._safe("Similar tracks", lambda: data.get_recommendations(track.track_id, 6), [])
        self._cache_tracks([row.track for row in rows])
        similar = self._table("#detail-similar-table")
        similar.clear()
        for row in rows:
            similar.add_row(
                f"{row.score:.3f}",
                str(row.track.track_id),
                row.track.name,
                self._artist_text(row.track),
                key=self._make_row_key("track", row.track.track_id),
            )

    def _refresh_inspector(self) -> None:
        # The inspector is intentionally redundant with the details screen: it
        # gives quick context while the user is on Search, Mood, Playlist, or
        # Catalog screens.
        track = self._selected_track()
        if track is None:
            self.query_one("#selected-title", Static).update("No track selected.")
            self.query_one("#selected-metadata", Static).update("")
            for selector in ("#meter-energy", "#meter-dance", "#meter-valence", "#meter-acoustic"):
                self.query_one(selector, ProgressBar).update(progress=0)
            return

        title = Text()
        # Rich Text lets us style parts of a label differently. Here the track
        # name is bright, artist is normal, and album is muted.
        title.append(track.name + "\n", style="bold #1ed760")
        title.append(self._artist_text(track) + "\n", style="#e7f7ed")
        title.append(track.album, style="#7f9b8c")
        self.query_one("#selected-title", Static).update(title)

        meters = {
            "#meter-energy": track.features.energy,
            "#meter-dance": track.features.danceability,
            "#meter-valence": track.features.valence,
            "#meter-acoustic": track.features.acousticness,
        }
        for selector, value in meters.items():
            # ProgressBar expects a 0-100 value, while Spotify audio features
            # are 0-1 decimals.
            self.query_one(selector, ProgressBar).update(progress=value * 100)

        metadata = (
            f"[b]TrackID[/] {track.track_id}\n"
            f"[b]Genres[/]\n{self._genre_text(track)}\n\n"
            f"[b]Duration[/] {format_duration(track.duration_ms)}\n"
            f"[b]Popularity[/] {track.popularity}/100\n"
            f"[b]Explicit[/] {'yes' if track.explicit else 'no'}\n"
            f"[b]Tempo[/] {track.features.tempo:.0f} BPM"
        )
        self.query_one("#selected-metadata", Static).update(metadata)

    def _mood_by_id(self, mood_id: int) -> MoodProfile | None:
        # Mood Select values are IDs. This helper finds the full loaded profile.
        return next((profile for profile in self.mood_profiles if profile.mood_id == mood_id), None)

    def _mood_copy(self, profile: MoodProfile | None, match_count: int | None) -> str:
        # The mood card is a small explanation of the backend's range filters.
        # Null min/max values mean that field is not constrained by the profile.
        if profile is None:
            return "No mood profile loaded."
        rows = [
            ("Energy", profile.min_energy, profile.max_energy, True),
            ("Danceability", profile.min_danceability, profile.max_danceability, True),
            ("Valence", profile.min_valence, profile.max_valence, True),
            ("Acousticness", profile.min_acousticness, profile.max_acousticness, True),
            ("Tempo", profile.min_tempo, profile.max_tempo, False),
            ("Loudness", profile.min_loudness, profile.max_loudness, False),
        ]
        ranges = "\n".join(f"{label}: {self._range_text(lo, hi, percent)}" for label, lo, hi, percent in rows)
        suffix = "" if match_count is None else f"\n\nMatches: {match_count} tracks"
        return f"[b #1ed760]{profile.name}[/]\n{ranges}{suffix}"

    def _range_text(self, low: float | None, high: float | None, percent: bool) -> str:
        # Convert numeric ranges into human-readable text. Percent fields are
        # audio features in [0, 1]. Tempo/loudness stay as raw numbers.
        if low is None and high is None:
            return "not constrained"
        if percent:
            left = format_percent(low) if low is not None else "any"
            right = format_percent(high) if high is not None else "any"
        else:
            left = f"{low:.1f}" if low is not None else "any"
            right = f"{high:.1f}" if high is not None else "any"
        return f"{left} to {right}"

    def _summary_copy(self, summary: dict[str, Any]) -> str:
        # Analytics summary is returned as one dictionary. This formats it into
        # a compact status card instead of another table.
        if not summary:
            return "Analytics unavailable until the backend is running."
        return (
            f"Tracks: {summary.get('TotalTracks', 0)}  |  "
            f"Artists: {summary.get('TotalArtists', 0)}  |  "
            f"Albums: {summary.get('TotalAlbums', 0)}  |  "
            f"Genres: {summary.get('TotalGenres', 0)}\n"
            f"Avg popularity: {float(summary.get('AvgPopularity') or 0):.1f}  |  "
            f"Avg energy: {format_percent(float(summary.get('AvgEnergy') or 0))}  |  "
            f"Avg valence: {format_percent(float(summary.get('AvgValence') or 0))}  |  "
            f"Avg tempo: {float(summary.get('AvgTempo') or 0):.0f} BPM"
        )

    def _track_detail_markup(self, track: Track) -> str:
        # Rich markup strings are accepted by Static widgets. This keeps the
        # overview card readable without building a separate table for metadata.
        return (
            f"[b #1ed760]{track.name}[/]\n"
            f"{self._artist_text(track)}\n"
            f"[#7f9b8c]{track.album}[/]\n\n"
            f"TrackID: {track.track_id}\n"
            f"Spotify ID: {track.spotify_track_id or ''}\n"
            f"Genres: {self._genre_text(track)}\n"
            f"Popularity: {track.popularity}/100\n"
            f"Duration: {format_duration(track.duration_ms)}\n"
            f"Explicit: {'yes' if track.explicit else 'no'}"
        )


def main() -> None:
    # Console-script entry point from pyproject.toml. Running
    # `spotify-explorer-tui` calls this function.
    SpotifyExplorerApp().run()
