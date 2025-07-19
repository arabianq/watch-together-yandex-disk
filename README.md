# Watch Together - Yandex Disk

`Watch Together` is a self-hosted web application that allows you and your friends to watch movies and TV shows in sync.
It uses Yandex.Disk for media file storage and fetches rich metadata from The Movie Database (TMDB) to create an elegant
browsing experience. The application is built with Python and the [NiceGUI](https://nicegui.io/) framework for a
seamless web interface.

## Features

* **Synchronized Playback:** Watch media with friends in real-time. The player state (play, pause, seek) is synchronized
  for everyone in a room.
* **Yandex.Disk Integration:** Leverages your Yandex.Disk account(s) as a media library.
* **TMDB Metadata:** Automatically fetches movie and TV show details, posters, and backdrops from TMDB.
* **Room Management:** Easily create and join watch party rooms.
* **User System:** A simple, password-protected login system to manage users.
* **Responsive UI:** A clean and modern web interface built with NiceGUI.

## File Naming Convention

For the application to correctly identify and process your media files, you must follow this naming scheme:

### Movies

- Files should be named in the format: `movie#{tmdb_id}#{name}.{extension}`
- **Example:** `movie#603#The Matrix.mp4`

### TV Shows

- Create a root directory named in the format: `tv#{tmdb_id}#{name}`
- **Example Root Directory:** `tv#1399#Game of Thrones`
- Inside this directory, place your episode files named in the format: `{season_number}#{episode_number}.{extension}`
- **Example Episode Files:** `1#1.mkv`, `1#2.mkv`, `2#1.mkv`

## Getting Started

Follow these instructions to get your own instance of Watch Together up and running.

### Prerequisites

* Python 3.12+
* `uv` package installer (recommended) or `pip`

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/arabianq/watch-together-yandex-disk.git
   cd watch-together-yandex-disk
   ```

2. **Install dependencies:**
   Using `uv` (recommended):
   ```bash
   uv sync
   ```
   Alternatively, using `pip`:
   ```bash
   pip install .
   ```

3. **Configuration:**
    * Create a `config.py` file by copying the example:
      ```bash
      cp config.py.example config.py
      ```
    * Edit `config.py` with your settings:
        * `YANDEX_CONFIGS`: Add your Yandex.Disk OAuth token(s) and the path to your media directory. You can get a
          token from the [Yandex.Disk API Polygon](https://yandex.com/dev/disk/poligon/).
        ```python
        # config.py
        YANDEX_CONFIGS = [
            ("y0_..._your_token", "/path/to/media/on/disk"),
            # You can add multiple accounts
        ]
        ```
        * `TMDB_API_KEY`: Add your API key from The Movie Database. You can get one by creating an account on
          their [website](https://www.themoviedb.org/signup) and registering for an API key.
        * `PASSWORD`: Set a password for the web UI login.
        * `SECRET`: Set a unique, random string for session security.
        * Review other settings like `HOST`, `PORT`, and cache options to fit your needs.

### Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Access the web interface:**
   Open your web browser and navigate to `http://<your-host>:<port>` (e.g., `http://127.0.0.1:8080`).

3. **Log in:**
   Use any username and the password you set in `config.py`.

4. **Start watching:**
   Browse your content, select a movie or show, and click "Create Room". Share the room URL with your friends to start
   watching together!

## Core Dependencies

This project relies on several key Python libraries:

* [NiceGUI](https://nicegui.io/): For building the web user interface.
* [yndx-disk](https://github.com/svetlov/yndx-disk): For asynchronous interaction with the Yandex.Disk API.
* [AIOHTTP](https://docs.aiohttp.org/): For making asynchronous HTTP requests to the TMDB API.
* [PyJWT](https://pyjwt.readthedocs.io/): For handling JSON Web Tokens for user sessions.
* [orjson](https://github.com/ijl/orjson): For fast JSON serialization/deserialization.
* [bcrypt](https://pypi.org/project/bcrypt/): For hashing user identifiers.