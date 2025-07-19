from dataclasses import dataclass
from typing import Sized


@dataclass(frozen=True)
class Content:
    tmdb_id: int = None

    vote_average: float = None

    adult: bool = None

    title: str = None
    og_title: str = None
    homepage: str = None
    poster_url: str = None
    backdrop_url: str = None
    release_date: str = None
    genres: tuple[Sized, ...] = None


@dataclass(frozen=True)
class Movie(Content):
    type: str = "movie"

    file_size: int = None
    budget: int = None
    runtime: int = None

    file_url: str = None


@dataclass(frozen=True)
class Episode:
    type: str = "episode"

    episode_number: int = None
    season_number: int = None
    runtime: int = None

    vote_average: float = None

    title: str = None
    file_url: str = None
    episode_type: str = None
    release_date: str = None


@dataclass(frozen=True)
class Season:
    type: str = "season"

    season_number: int = None
    episodes_count: int = None

    vote_average: float = None

    title: str = None
    poster_url: str = None
    release_date: str = None

    episodes: tuple[Episode, ...] = None


@dataclass(frozen=True)
class TVShow(Content):
    type: str = "tv"

    number_of_episodes: int = None
    number_of_seasons: int = None

    in_production: bool = None

    seasons: tuple[Season, ...] = None
