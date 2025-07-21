import asyncio
import logging
import random

import aiohttp
from cachetools import TTLCache
from cachetools_async import cached

import config
from movies.classes import Movie, TVShow, Season, Episode

_BASE_API_URL = "https://api.themoviedb.org/3"
_BASE_IMAGE_URL = None

_TMDB_REQUEST_SEMAPHORE = asyncio.Semaphore(config.TMDB_CONCURRENT_REQUESTS_LIMIT)


async def _make_tmdb_request(session: aiohttp.ClientSession, url: str, params: dict = None) -> dict:
    async with _TMDB_REQUEST_SEMAPHORE:
        headers = {
            "Authorization": f"Bearer {config.TMDB_API_KEY}",
            "Accept": "application/json"
        }
        request_params = {"language": config.TMDB_LANG, **(params or {})}

        try:
            async with session.get(url=url, headers=headers, params=request_params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logging.error("TMDB request failed for %s: Status %s, Response: %s", url, e.status, e.message)
            raise
        except aiohttp.ClientError as e:
            logging.error("Network error during TMDB request for %s: %s", url, e)
            raise


async def _get_client_session() -> aiohttp.ClientSession:
    proxy = random.choice(config.PROXIES) if config.PROXIES else None
    return aiohttp.ClientSession(proxy=proxy)


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_tmdb_configuration():
    global _BASE_IMAGE_URL

    logging.info("Fetching TMDB configuration data")

    async with await _get_client_session() as session:
        response_json = await _make_tmdb_request(session, f"{_BASE_API_URL}/configuration")

    _BASE_IMAGE_URL = response_json["images"]["base_url"]


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_movie(movie: Movie) -> Movie:
    logging.info("Fetching movie data for TMDB ID: %s", movie.tmdb_id)

    async with await _get_client_session() as session:
        response_json = await _make_tmdb_request(session, f"{_BASE_API_URL}/movie/{movie.tmdb_id}")

    return Movie(
        tmdb_id=movie.tmdb_id,
        file_size=movie.file_size,
        file_url=movie.file_url,
        title=response_json.get("title", movie.title),
        budget=response_json.get("budget"),
        runtime=response_json.get("runtime"),
        vote_average=response_json.get("vote_average"),
        adult=response_json.get("adult"),
        og_title=response_json.get("original_title"),
        homepage=response_json.get("homepage"),
        poster_url=f"{_BASE_IMAGE_URL}original{response_json['poster_path']}" if response_json.get(
            "poster_path") else None,
        backdrop_url=f"{_BASE_IMAGE_URL}original{response_json['backdrop_path']}" if response_json.get(
            "backdrop_path") else None,
        release_date=response_json.get("release_date"),
        genres=tuple(sorted([genre["name"].capitalize() for genre in response_json.get("genres", [])], key=len)),
    )


async def _fetch_tv_season_data(session: aiohttp.ClientSession, tv_show_id: int, season_number: int) -> dict:
    logging.debug("Fetching season %s data for TV show TMDB ID: %s", season_number, tv_show_id)
    return await _make_tmdb_request(session, f"{_BASE_API_URL}/tv/{tv_show_id}/season/{season_number}")


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_tv_show(tv_show: TVShow) -> TVShow:
    logging.info("Fetching TV show data for TMDB ID: %s", tv_show.tmdb_id)

    async with await _get_client_session() as session:
        tv_response_json = await _make_tmdb_request(session, f"{_BASE_API_URL}/tv/{tv_show.tmdb_id}")

        season_tasks = [
            _fetch_tv_season_data(session, tv_show.tmdb_id, season.season_number)
            for season in tv_show.seasons
        ]
        seasons_data_jsons = await asyncio.gather(*season_tasks)

    raw_seasons_map = {s.season_number: s for s in tv_show.seasons}

    processed_seasons_list = []
    for season_response_json in seasons_data_jsons:
        season_number = season_response_json["season_number"]
        raw_season = raw_seasons_map.get(season_number)

        if not raw_season:
            logging.warning("Skipping season %s for TV show %s as it's not in raw data.", season_number,
                            tv_show.tmdb_id)
            continue

        raw_episodes_map = {e.episode_number: e for e in raw_season.episodes}
        processed_episodes = []

        for episode_response_json in season_response_json.get("episodes", []):
            episode_number = episode_response_json["episode_number"]
            raw_episode = raw_episodes_map.get(episode_number)

            if not raw_episode:
                logging.warning("Skipping episode %s:%s for TV show %s as it's not in raw data.",
                                season_number, episode_number, tv_show.tmdb_id)
                continue

            processed_episodes.append(Episode(
                episode_number=episode_number,
                season_number=season_number,
                runtime=episode_response_json.get("runtime"),
                vote_average=episode_response_json.get("vote_average"),
                title=episode_response_json.get("name", str(episode_number)),
                file_url=raw_episode.file_url,
                still_url=f"{_BASE_IMAGE_URL}original{episode_response_json['still_path']}" if tv_response_json.get(
                    "poster_path") else None,
                episode_type=episode_response_json.get("episode_type"),
                release_date=episode_response_json.get("air_date"),
            ))

        processed_seasons_list.append(Season(
            season_number=season_number,
            episodes_count=len(processed_episodes),
            vote_average=season_response_json.get("vote_average"),
            title=season_response_json.get("name", str(season_number)),
            poster_url=f"{_BASE_IMAGE_URL}original{season_response_json['poster_path']}" if season_response_json.get(
                "poster_path") else None,
            release_date=season_response_json.get("air_date"),
            episodes=tuple(processed_episodes)
        ))

    processed_seasons_list.sort(key=lambda s: s.season_number)

    return TVShow(
        tmdb_id=tv_show.tmdb_id,
        number_of_episodes=tv_show.number_of_episodes,
        number_of_seasons=len(processed_seasons_list),
        vote_average=tv_response_json.get("vote_average"),
        adult=tv_response_json.get("adult"),
        title=tv_response_json.get("name"),
        og_title=tv_response_json.get("original_name"),
        homepage=tv_response_json.get("homepage"),
        poster_url=f"{_BASE_IMAGE_URL}original{tv_response_json['poster_path']}" if tv_response_json.get(
            "poster_path") else None,
        backdrop_url=f"{_BASE_IMAGE_URL}original{tv_response_json['backdrop_path']}" if tv_response_json.get(
            "backdrop_path") else None,
        release_date=tv_response_json.get("first_air_date"),
        in_production=tv_response_json.get("in_production"),
        seasons=tuple(processed_seasons_list),
        genres=tuple(sorted([genre["name"].capitalize() for genre in tv_response_json.get("genres", [])], key=len)),
    )


async def _fetch_data(content: Movie | TVShow) -> Movie | TVShow:
    logging.info("Fetching data for %s: %s", content.type, content.tmdb_id)

    match content.type:
        case "movie":
            return await _fetch_movie(content)
        case "tv":
            return await _fetch_tv_show(content)
        case _:
            raise TypeError(f"Unknown content type: {content.type}")


async def fetch_all_data(contents: list[Movie | TVShow]) -> list[Movie | TVShow]:
    logging.info("Fetching data for %s contents", len(contents))

    await _fetch_tmdb_configuration()

    tasks = [_fetch_data(content) for content in contents]
    return await asyncio.gather(*tasks)
